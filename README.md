
# Deploying a Spark Cluster on AWS Academy

This repository contains a guided procedure for deploying a Spark cluster for teaching purposes inside AWS Academy. The cluster uses a **Controller** machine to orchestrate the deployment of a Spark cluster through [Flintrock](https://github.com/nchammas/flintrock), with EC2 instances for computing and S3 for persistent storage.

This is not intended for production use, but as an academic resource to practice the deployment and operation of distributed big data infrastructure.

## Repository Structure

- `config/flintrock/`: Flintrock configuration for cluster provisioning
- `config/spark/`: Spark configuration files deployed to the cluster master
- `config/hadoop/`: Hadoop configuration files deployed by Flintrock
- `credentials/aws/`: Template for AWS session credentials
- `scripts/`: Utility scripts for cluster operations and testing

When referring to the **AWS Academy Console** it corresponds to the regular AWS Management Console, but accessed through the AWS Academy portal. The services and features are the same as in the regular console, but the available resources will be provided and limited by the AWS Academy environment.

## Initial AWS Preparation

### Create the EC2 key pair

In the AWS Academy console go to **EC2** and then:

- Open **Network & Security** → **Key Pairs**
- Click **Create key pair**
- Name the key `cluster-key`
- Use an **RSA** key
- Use the **.pem** format
- Download the key to your computer

If you want to keep your local material organized, you may store the key inside `.ssh/` for easy access from the terminal. The important thing is to remember where you stored it, because you will need it both to connect to the Controller machine and to upload it to the Controller later.

> ⚠️ Warning: You cannot download the same key pair again. If you lose the `.pem` file, you will not be able to connect to any machine that uses that key pair

### Create the security group

You must create a security group that allows SSH access to the Controller machine:

- Open **Network & Security** → **Security Groups**
- Click **Create security group**
- Name the group `spark-cluster-sg` with a description like "Security group for the Spark cluster" and VPC to the default one provided by AWS
- In **Inbound rules** add a rule with:
  - Type: `SSH`
  - Port: `22`
  - Source: `Anywhere-IPv4`
- In **Outbound rules** there should be a single rule allowing all traffic configured by default. You must leave it as is
- Click **Create security group**

> 💡 Note: Flintrock will automatically create its own security group (`flintrock-spark-cluster`) to handle communication between the Spark cluster machines. You do not need to configure that manually

### Create the S3 data bucket

Go to the S3 service and:

- Click on **Create bucket**
- Name your bucket following the pattern `XXXXXXXX-X-spark-data` where `XXXXXXXX-X` is your student RUT without dots (e.g., `12345678-k-spark-data`)
- Click on **Create bucket**

> 💡 Note: The bucket naming pattern is for standardization. You may use any name you prefer, but you will need to update the test scripts accordingly

## Creating the Controller Machine

### Create the Controller instance

Go to **EC2** → **Instances**, and click **Launch instances**. Configure the instance with:

- Name: `Controller`
- Operating system: `Ubuntu Server 24.04`
- Instance type: `t3.large`
- Key pair: the key created in the previous step
- Network settings: Select existing security group and then select `spark-cluster-sg`
- Storage: `20 GB` `gp3`

Click **Launch instance** and then **View all instances**. Wait until the Controller instance is in state running before proceeding.

### Elastic IP for the Controller

In AWS, each time a machine is stopped and started again, it may receive a different public IP. To maintain a fixed public IP for the Controller, associate an Elastic IP to it:

- Open **Network & Security** → **Elastic IPs**
- Click **Allocate Elastic IP address**
- Use the default options and click **Allocate**
- After the Elastic IP is allocated, select it and click **Actions** → **Associate Elastic IP address**
- In the association form, select the Controller instance (it is not necessary to select a specific private IP)
- Click **Associate**
- Take note of the Elastic IP, which is the new public IP of the Controller. You will use it to connect to the Controller throughout this procedure

### Testing the SSH connection to the Controller

Before proceeding, test that you can connect to the Controller through SSH using the `.pem` key. In the terminal, go to the folder that contains the `.pem` file, then run:

On Linux or macOS:

```bash
chmod 400 cluster-key.pem
ssh -i cluster-key.pem ubuntu@<controller_public_ip>
```

On Windows you may need to adjust permissions before connecting. First get your username with `whoami`, then run:

```powershell
icacls cluster-key.pem /reset
icacls cluster-key.pem /grant <username>:F
```

Then you can connect with:

```bash
ssh -i cluster-key.pem ubuntu@<controller_public_ip>
```

The first time you connect, you must accept the server fingerprint. If the connection is successful, you should see a welcome message from the Ubuntu server and a command prompt. Once you confirm that the SSH connection is working, you can disconnect with `exit` and proceed to the next steps.

## Configuring the Controller

### Base Installation

Connect to the Controller, update packages and install the required dependencies:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install pipx zip python-is-python3 python3-boto3 -y
pipx ensurepath
```

### Install AWS CLI

AWS CLI allows you to manage AWS services from the command line and is required by Flintrock to interact with EC2:

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip aws
```

### Make This Repository Available on the Controller

Clone the current repository and place it in `/opt/`:

```bash
cd /tmp
git clone https://github.com/ptoledo-teaching/dataengineering-spark.git
sudo mv dataengineering-spark /opt/dataengineering-spark
```

This will leave the repository in:

```bash
/opt/dataengineering-spark
```

### Install Flintrock

[Flintrock](https://github.com/nchammas/flintrock) is a tool that automates the deployment and configuration of Spark clusters on EC2. Because of certain account and permission restrictions in AWS Academy, the Flintrock package must be patched before use. The patch script included in this repository applies all required fixes automatically.

To install and patch Flintrock, run the following from your **home directory** (`~`):

```bash
cd ~
pipx uninstall flintrock 2>/dev/null; pipx install flintrock
python3 /opt/dataengineering-spark/scripts/patch.py
```

> ⚠️ Important: The patch script must be run from the home directory (`~`) because it resolves internal Flintrock file paths relative to that location

### Configure a Spark-Specific Environment on the Controller

The repository includes `scripts/spark-env.sh`, a shell snippet that adds the repository's management scripts to your `PATH` so they can be invoked directly from any directory.

To have a shortcut for loading the Spark environment, create a symbolic link to that file in your home folder:

```bash
ln -s /opt/dataengineering-spark/scripts/spark-env.sh ~/spark-env.sh
```

Then, whenever you want to work with the cluster in that shell session, load it with:

```bash
source ~/spark-env.sh
```

### Reboot the Controller

Reboot the Controller to ensure all package updates and environment changes take effect:

```bash
sudo reboot
```

After the reboot, reconnect using the same SSH command as before.

## Cluster Configuration

### Upload SSH Credentials

The Controller needs the `cluster-key.pem` file to create and connect to the Spark cluster machines. You must put the key in the `/opt/dataengineering-spark/credentials/keys` folder in the Controller machine (you must create the folder) and be sure that it has 400 permissions.

### Set AWS User Credentials

> ⚠️ Important: The AWS session token changes with each session and must be updated every time you start the lab

Create a copy of the example aws credentials files inside the repo:

```bash
cd /opt/dataengineering-spark
cp credentials/aws/credentials.sh.template credentials/aws/credentials.sh
```

In the page where you launched the AWS Academy session, go to **AWS Details** → **Cloud Access** → **AWS CLI** → **show** to get your account credentials. Open `credentials/aws/credentials.sh` and fill in the three values:

```bash
export AWS_ACCESS_KEY_ID=<your_access_key>
export AWS_SECRET_ACCESS_KEY=<your_secret_key>
export AWS_SESSION_TOKEN=<your_session_token>
```

> ⚠️ Important: Please notice that the format of the information available in the AWS Academy Canvas website is different from the one required by the template credentials.sh file

## Managing the Cluster

To run any cluster management command, you must be connected to the Controller and have the Spark environment loaded with `source ~/spark-env.sh`.

### Launching the Cluster

Run the launch script to deploy and configure the Spark cluster:

```bash
launch.sh
```

This script uses `config/flintrock/config.yaml` to configure the cluster. You may edit `/opt/dataengineering-spark/config/flintrock/config.yaml` before launching if you want to:

- Change the instance type for the workers (default: `t2.micro`)
- Modify the number of workers (default: `2`)

Expected runtime: 2–4 minutes. If deployment fails, the script will ask whether to keep or delete the created machines.

### Connecting to the Cluster Master

To open an SSH session to the Spark cluster Master node:

```bash
login.sh
```

### Destroying the Cluster

To terminate all cluster EC2 instances:

```bash
destroy.sh
```

This keeps all configurations intact (S3 bucket, credentials, and keys). You may see residual security groups named `flintrock` or `flintrock-spark-cluster`. These can be deleted manually from the AWS console.

## Usage on the Cluster Master Machine

Once connected to the Cluster Master through `./login.sh`, the following scripts are available in `~/scripts/`:

### `clean.sh`

Goes through each worker and removes temporary Spark working files to free disk space:

```bash
~/scripts/clean.sh
```

### `get_usage.sh`

Reports CPU and memory usage for the Master and each Worker. The first column is the Master, followed by each Worker.

```bash
~/scripts/get_usage.sh
```

By default, it samples every 5 seconds. To change the interval:

```bash
~/scripts/get_usage.sh 10
```

### `submit.sh`

Wrapper for `spark-submit` that handles AWS credential injection. Accepts one parameter: the script to submit:

```bash
~/scripts/submit.sh <script.py>
```

## Testing

Two test scripts are provided to verify the Spark setup. They must be run from the Cluster Master machine after connecting via `./login.sh`.

### `test-000.sh`

A basic distributed map-reduce script that computes the sum of the first 1 million natural numbers squared:

```bash
~/scripts/test-000.sh
```

The output is saved in `~/scripts/test-000.log`. The expected result is:

```
Sum of squares: 333332833333500000
```

### `test-001.sh`

Tests S3 integration and PySpark SQL features by loading reference astronomical data and executing SQL operations.

Before running this test:

1. Scale the cluster to at least **7 workers** with instance type **t2.medium** in `config/flintrock/config.yaml` on the Controller, then redeploy with `./launch.sh`
2. Set your bucket name by editing line 9 of `~/scripts/test-001.py` on the Cluster Master

Run with:

```bash
~/scripts/test-001.sh
```

The expected log should report:

```
Reading file vlt_observations_000.csv from paranal-data bucket
Writing file as vlt_observations_000.parsed.parquet into 12345678-k-spark-data bucket
```

And the following folders should appear in your S3 bucket:

- `vlt_observations_000.parquet`
- `vlt_observations_000.parsed.csv`
- `vlt_observations_000.parsed.parquet`

## Final Notes

### Shut Down the Cluster

To stop the Spark cluster without losing configuration, run from the Controller:

```bash
destroy.sh
```

This terminates all cluster EC2 instances but keeps the Controller, the S3 bucket, and all credentials intact. You can redeploy the cluster at any time with `./launch.sh`.

To stop the Controller machine itself, go to the AWS Academy console, select the Controller instance, and use **Instance state** → **Stop instance**. The machine (including `/opt/dataengineering-spark/` and all credentials) will be preserved for the next session.

### About the AWS Academy Session

Each time the AWS Academy session starts, it starts a timer of 4 hours. When the timer ends, all resources are stopped automatically. You can check the remaining time in the AWS Academy Canvas website. If you need more time, click **Start Lab** again to reset the timer.

When an AWS Academy session starts, it automatically restarts all EC2 machines. When the session ends, all machines are stopped to prevent resource usage when not needed. Because of this, the AWS credentials in `credentials/aws/credentials.sh` will be invalid at the start of each new session and must be updated before launching the cluster again.
