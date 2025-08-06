
# Data Engineering - Deploying a Spark Cluster on AWS Academy

This repository is intended to provide the instructions to deploy a Spark Cluster for academic purposes within the AWS Academy environment.

The tools enclosed in this repo will allow you to easily create, log into, and destroy a Spark-based cluster that uses EC2 for the machines and S3 as permanent storage, in order to develop and test distributed software developments intended for big data analysis.

## Initial Set-Up

### Create data bucket

Go into the AWS Console provided by AWS Academy, then go to the S3 service and:

- Click on `Create bucket`
- Name you bucket with your rut as `12345678-K-dde`
- Click in `Create bucket`

### Create the controller instance

Go to the EC2 service and:

- Go to `Network & Security` -> `Key Pairs` and:
  - Create a key pair to access your future cluster. Name ir `cluster-key` in .pem format. This will automatically download a `cluster-key.pem` that you need to store in a safe place
- Go to `Instances` -> `Insatances` and click on `Launch instances`. You should use the default configuration with the following changes:
  - Application and OS Images
    - Select Ubuntu as the OS
    - Select the image `Ubuntu Server 24.04`
  - Instace Type
    - Select the instance type `t2.large`
  - Key pair
    - Select `cluster-key` (the key that you created in the previous step)
  - Configure storage
    - Change the volume size from 8 to 20
- Go to `Network & Security` -> `Elastic IPs` and:
  - Click on `Allocate Elastic IP address` and then click on `Allocate`
  - Click on the IP address that was allocated
  - Take not of this IP, as it will be the ip you will be using to connect to your cluster
  - Click on `Associate Elastic IP address`
  - Click on the `instance` input and select the EC2 machine that drops down (it is the machine you just created in the previous step)
  - Click on `Associate`

### Connect to the machine
In your computer, open a terminal and then:

- Go to the folder where you stored de cluster-key.pem file
- ⚠️ If you are in linux, you should execute `chmod 400 cluster-key.pem` this step is NOT required if you are in windows
- Run the command `ssh -i cluster-key.pem ubuntu@<ip>`
  - You will get a message similar to `The authenticity of host '52.70.173.29 (52.70.173.29)' can't be established.`
  - You should type `yes` to accept the fingerprint
- With this you have connected to the main cluster server

## Installation

Once you have connected to the main cluster server, we can proceed with the base installation: 

### Update your system

You must update the system packages and installing the basic requirements by running

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install zip python-is-python3 -y
```

### Clone Repository

You must clone this repository that includes all the required code. You can do this by typing the following command in the terminal:

```bash
git clone https://github.com/ptoledo-teaching/dataengineering-spark.git
```

### Install AWS CLI

AWS CLI is the Amazon Web Services Command Line Interface. It allows you to manage AWS services from your command line.

Installation instructions can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). In summary, copy and execute the following lines in the terminal

```bash
sudo apt install zip
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
```

### Install Boto3

**Boto3** is a Python library for accessing AWS services programmatically.

```bash
sudo apt install python3-boto3
```

### Install Flintrock

[https://github.com/nchammas/flintrock|Flintrock] is an independent project that will help us to automatically deploy and configure the cluster. You can should install it by running:

```bash
sudo apt install pipx -y
pipx ensurepath
pipx install flintrock
```

### Restarting server

You must restar the server for the installation to work correctly. You can do this by running:
```bash
sudo reboot
```
This will log you out, and you must login again the same way as before.

## Cluster configuration

### AWS User Credentials

1. In `credentials/aws/`, copy `credentials.sh.template` to `credentials.sh` by 
2. Go to your lab initialization page in Canvas
3. Click on **AWS Details**
4. Complete the `credentials.sh` file with the informations that appear under **AWS CLI**

#### If you are using a personal AWS Account

1. Go to the [IAM Users console](https://us-east-1.console.aws.amazon.com/iam/home?region=us-east-1#/users) and create a new programmatic user (e.g., **flintrock**).
2. Assign the **AdministratorAccess** policy directly.
3. After creation, go to the **Security credentials** tab → **Access keys** → Create a new access key.
4. In `credentials/aws/`, copy `credentials.sh.template` to `credentials.sh` and add the generated key ID and secret.
5. Delete the line `export AWS_SESSION_TOKEN=`

Update the `bucket` variable in `scripts/test-001.py` with your bucket name.

## Usage on User Host

Scripts provided:

- `launch.sh` — Deploys the cluster
- `login.sh` — SSH into the master node
- `destroy.sh` — Destroys the cluster

### launch.sh

Uses `config/`, `credentials/`, and `scripts/` to deploy and configure your cluster.

You may need to edit `config/flintrock/config.yaml` if:

- Changing instance type (default: `t2.micro`)
- Updating the AMI ID (subject to change)
- Modifying number of workers (default: 2)

If deployment fails, the script will prompt you about keeping or deleting the created machines.

Expected runtime: 2–4 minutes.

### login.sh

Connects you to the master machine via SSH.

### destroy.sh

Destroys EC2 instances but leaves other configurations (S3 bucket, keys, etc.) intact.

You may see residual EC2 security groups named `flintrock` or `flintrock-spark-cluster`. These can be deleted manually.

## Usage on Master Host

The `scripts` directory contains the following commands:

### clean.sh

Cleans the `~/spark/work` directory on each worker to free disk space.

### get_usage.sh

Reports CPU and memory usage for each machine. The first column is the master, followed by workers.

The script uses a default interval of 5 seconds.

```bash
./get_usage.sh
```

You can use an integer parameter to change the refresh interval:

```bash
./get_usage.sh 10  # every 10 seconds
```

### submit.sh

Wrapper for `spark-submit`. Accepts one parameter: the script to submit.

## Testing

Run these tests after deployment to verify setup.

### test-000.sh

A simple distributed map-reduce script.

Output: terminal log and `scripts/test-000.log`.

Example:
```
Sum of squares: 333332833333500000
```

### test-001.sh

Tests S3 integration and PySpark SQL features.

Output: `scripts/test-001.log`.

Example:
```
Reading file vlt_observations_000.csv from utfsm-inf356-datasets bucket
Writting file as vlt_observations_000.parsed.parquet into XXXXXXXXXX-inf356 bucket
```

Check your S3 bucket for:

- `vlt_observations_000.parquet`
- `vlt_observations_000.parsed.csv`
- `vlt_observations_000.parsed.parquet`
