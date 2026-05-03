#!/bin/bash
SPARK_DIR=/opt/dataengineering-spark
FLINTROCK_CONFIG=$SPARK_DIR/config/flintrock/config.yaml
TARGET_MASTER_INSTANCE_TYPE=t3.large
SSH_KEY="$SPARK_DIR/credentials/keys/cluster-key.pem"

source "$SPARK_DIR/credentials/aws/credentials.sh"

AWS_REGION=$(awk '/^[[:space:]]*region:/{print $2; exit}' "$FLINTROCK_CONFIG")

if [ -z "$AWS_REGION" ]; then
    echo "Error: could not determine the AWS region from $FLINTROCK_CONFIG."
    exit 1
fi

log_step() {
    echo "### $1"
}

wait_for_instance_state() {
    target_state="$1"
    instance_id="$2"
    attempt=1

    while true; do
        current_state=$(aws ec2 describe-instances \
            --region "$AWS_REGION" \
            --instance-ids "$instance_id" \
            --query 'Reservations[0].Instances[0].State.Name' \
            --output text)
        log_step "Master state check $attempt: current=$current_state target=$target_state"
        if [ "$current_state" = "$target_state" ]; then
            break
        fi
        attempt=$((attempt + 1))
        sleep 5
    done
}

wait_for_instance_status_ok() {
    instance_id="$1"
    attempt=1

    while true; do
        status_line=$(aws ec2 describe-instance-status \
            --region "$AWS_REGION" \
            --include-all-instances \
            --instance-ids "$instance_id" \
            --query 'InstanceStatuses[0].[InstanceState.Name,SystemStatus.Status,InstanceStatus.Status]' \
            --output text 2>/dev/null)

        if [ -z "$status_line" ] || [ "$status_line" = "None" ]; then
            state="unknown"
            system_status="unknown"
            instance_status="unknown"
        else
            state=$(echo "$status_line" | awk '{print $1}')
            system_status=$(echo "$status_line" | awk '{print $2}')
            instance_status=$(echo "$status_line" | awk '{print $3}')
        fi

        log_step "Master health check $attempt: state=$state system=$system_status instance=$instance_status"
        if [ "$state" = "running" ] && [ "$system_status" = "ok" ] && [ "$instance_status" = "ok" ]; then
            break
        fi
        attempt=$((attempt + 1))
        sleep 10
    done
}

wait_for_ssh() {
    host="$1"
    attempt=1

    while true; do
        if ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no -o ConnectTimeout=10 "ec2-user@$host" true 2>/dev/null; then
            log_step "SSH is ready on $host"
            break
        fi
        log_step "SSH check $attempt: $host is not ready yet"
        attempt=$((attempt + 1))
        sleep 5
    done
}

log_step "Using AWS region $AWS_REGION"
log_step "Launching cluster"
flintrock --config "$FLINTROCK_CONFIG" launch spark-cluster
IP_MASTER=$(flintrock --config "$FLINTROCK_CONFIG" describe spark-cluster 2>/dev/null | grep master: | awk '{print $2}')

if [ -z "$IP_MASTER" ]; then
    echo "Error: could not determine the Spark master host."
    exit 1
fi

log_step "Detected Spark master host: $IP_MASTER"
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "ec2-user@$IP_MASTER" 'ssh -o StrictHostKeyChecking=no ec2-user@$(hostname) "mkdir -p scripts"' 2>/dev/null
log_step "Transferring files to master node"
scp -i "$SSH_KEY" "$SPARK_DIR"/scripts/* "ec2-user@$IP_MASTER:~/scripts"
scp -i "$SSH_KEY" "$SPARK_DIR"/config/spark/* "ec2-user@$IP_MASTER:~/spark/conf/"
scp -i "$SSH_KEY" "$SPARK_DIR/credentials/aws/credentials.sh" "ec2-user@$IP_MASTER:~/scripts"
ssh -i "$SSH_KEY" -T "ec2-user@$IP_MASTER" << EOF
    echo "### Configuring master node"
    sudo yum -y -q update
    chmod +x ~/scripts/*.sh
    echo 'export PATH=\$PATH:~/scripts' >> ~/.bashrc
    chmod +x ~/scripts/*.sh
    echo "### Configuring worker nodes"
    for slave in \$(cat ~/spark/conf/slaves); do
        echo \$slave
        scp ~/spark/conf/spark-defaults.conf ec2-user@\$slave:~/spark/conf/ &
        wait
    done
EOF

MASTER_INSTANCE_ID=$(aws ec2 describe-instances \
    --region "$AWS_REGION" \
    --filters "Name=instance-state-name,Values=pending,running,stopping,stopped" \
    --query 'Reservations[].Instances[].[InstanceId,PublicIpAddress,PublicDnsName]' \
    --output text | awk -v master="$IP_MASTER" '$2 == master || $3 == master {print $1; exit}')

if [ -z "$MASTER_INSTANCE_ID" ]; then
    echo "Error: could not resolve the EC2 instance ID for the Spark master ($IP_MASTER)."
    exit 1
fi

log_step "Resolved Spark master instance ID: $MASTER_INSTANCE_ID"

MASTER_INSTANCE_TYPE=$(aws ec2 describe-instances \
    --region "$AWS_REGION" \
    --instance-ids "$MASTER_INSTANCE_ID" \
    --query 'Reservations[0].Instances[0].InstanceType' \
    --output text)

if [ "$MASTER_INSTANCE_TYPE" != "$TARGET_MASTER_INSTANCE_TYPE" ]; then
    log_step "Master instance type is $MASTER_INSTANCE_TYPE"
    log_step "Resizing master node to $TARGET_MASTER_INSTANCE_TYPE"
    log_step "Sending stop request to EC2"
    aws ec2 stop-instances --region "$AWS_REGION" --instance-ids "$MASTER_INSTANCE_ID" >/dev/null
    log_step "Waiting for the master instance to stop"
    wait_for_instance_state stopped "$MASTER_INSTANCE_ID"
    log_step "Modifying instance type in EC2"
    aws ec2 modify-instance-attribute \
        --region "$AWS_REGION" \
        --instance-id "$MASTER_INSTANCE_ID" \
        --instance-type "{\"Value\":\"$TARGET_MASTER_INSTANCE_TYPE\"}"
    log_step "Sending start request to EC2"
    aws ec2 start-instances --region "$AWS_REGION" --instance-ids "$MASTER_INSTANCE_ID" >/dev/null
    log_step "Waiting for the master instance to reach running state"
    wait_for_instance_state running "$MASTER_INSTANCE_ID"
    log_step "Waiting for EC2 health checks to pass"
    wait_for_instance_status_ok "$MASTER_INSTANCE_ID"
    IP_MASTER=$(aws ec2 describe-instances \
        --region "$AWS_REGION" \
        --instance-ids "$MASTER_INSTANCE_ID" \
        --query 'Reservations[0].Instances[0].PublicIpAddress' \
        --output text)
    log_step "Master public IP after restart: $IP_MASTER"
    log_step "Waiting for SSH on restarted master"
    wait_for_ssh "$IP_MASTER"
    ssh -i "$SSH_KEY" -T "ec2-user@$IP_MASTER" << EOF
        echo "### Restarting Spark master service"
        ~/spark/sbin/start-master.sh
        for attempt in \$(seq 1 12); do
            if ss -ltn | grep -q ':7077 '; then
                echo "### Spark master is listening on port 7077"
                exit 0
            fi
            echo "### Spark master port check \$attempt: 7077 not ready yet"
            sleep 5
        done
        echo "Error: Spark master did not start on port 7077." >&2
        exit 1
EOF
    log_step "Master node restarted as $TARGET_MASTER_INSTANCE_TYPE ($IP_MASTER)"
else
    log_step "Master node already using $TARGET_MASTER_INSTANCE_TYPE"
fi

log_step "Ready"
