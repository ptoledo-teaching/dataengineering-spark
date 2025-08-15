
# Deploying a Spark Cluster on AWS Academy

This repository is intended to provide the instructions to deploy a Spark Cluster for academic purposes within the AWS Academy environment. Together with this, this repo contains several scripts to facilitate the deployment and management of the cluster.

The tools enclosed in this repo will allow you to easily create, log into, and destroy a Spark-based cluster that uses EC2 for computing and S3 for permanent storage, in order to develop and test distributed software developments intended for big data analysis.

This repo is not intended for production use, but as an academic resource to train data engineers in the use of big data distributed infrastructure.

## Initial Set-Up

### Create data bucket

Go into the AWS Console provided by AWS Academy, then go to the S3 service and:

- Click on **Create bucket**
- Name you bucket with your rut following this pattern **12345678-k-dde**
- Click in **Create bucket**

> 💡 **Note**: The bucket naming pattern is for standardization, you can name you bucket in any way you like if the name is already taken or if you want to use something specific

### Create the controller instance

Go to the EC2 service and:

- Go to **Network & Security** → **Key Pairs** and:
  - Click on **Create key pair**
  - Set the key name to **cluster-key**
  - The **Key pair type** must be **RSA**
  - The **Private key file format** must be **.pem**
  - Click on **Create key pair**. This will automatically download a **cluster-key.pem** file to your computer
> 💡 **Note**: The tutorial scripts assume key it is called **cluster-key.pem**, but this is not required; nevertheless, if you want to use another name you will need to update the repo scripts accordingly
- Go to **Instances** → **Instances** and click on **Launch instances**. You must use the default configuration with the following changes:
  - Name your instance **Cluster Controller**
  - Application and OS Images
    - Select **Ubuntu** as the OS
    - Select the image **Ubuntu Server 24.04**
  - Instance Type
    - Select the instance type **t2.large**
  - Key pair
    - Select **cluster-key** (the key that you created in the previous step)
  - Configure storage
    - Change the volume size from 8 to 20
- Go to **Network & Security** → **Elastic IPs** and:
  - Click on **Allocate Elastic IP address** and then click on **Allocate**
  - Click on the IP address that was allocated
  - **Take note of this IP, as it will be the ip you will be using to connect to your cluster**
  - Click on **Associate Elastic IP address**
  - Click on the **instance** input and select the EC2 machine you created in the previous step
  - Click on **Associate**

### Connect to the machine

> ⚠️ **Note**: Consider this information if you encounter an error when connecting to the instance because of file permissions
>
> - **Linux or Mac**: you should execute `chmod 400 cluster-key.pem` in the folder where you stored the **cluster-key.pem** file. This sets the key permissions to read-only for the owner, something that is required for security reasons
> 
> - **Windows**: You might require to adjust the key permissions. First, get you username by running `whoami` in the terminal, then, run the command `icacls cluster-key.pem /reset` and finally run `icacls cluster-key.pem /grant <username>:F` where **<username>** is your Windows username.

- Go to the folder where you stored de cluster-key.pem file
- Run the command 
  ```bash
  ssh -i cluster-key.pem ubuntu@<ip_address>
  ```
- The first time you connect, you should get a message similar to:
  ```bash
  The authenticity of host '52.70.173.29 (52.70.173.29)' can't be established.
  ```
- This is because you are connecting to a machine that is unknown to your system. You should type **yes** to accept the fingerprint of your server
- After this, you should have connected to the main cluster server and you should get a terminal that looks similar to:
  ```bash
  ubuntu@ip-172-31-24-123:~$
  ```

## Installation

Once it has been possible to connect to the main cluster server, we can proceed with the installation of the required software.

### Update your system

You must start by updating the system packages and installing the basic requirements by running:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install pipx zip python-is-python3 python3-boto3 -y
pipx ensurepath
```

### Clone Repository

You must clone this repository that includes all the required code. You can do this by typing the following command:

```bash
git clone https://github.com/ptoledo-teaching/dataengineering-spark.git
```

### Install AWS CLI

AWS CLI is the Amazon Web Services Command Line Interface. It allows you to manage AWS services from your command line.

Installation instructions can be found [here](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html). In summary, copy and execute the following lines in the terminal

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install
rm -rf awscliv2.zip aws
```

### Install Flintrock

[Flintrock](https://github.com/nchammas/flintrock) is an independent project designed to automatically deploy and configure spark clusters; nevertheless, in order to bypass certain account and permission issues, the Flintrock package must be patched. The following command assures a clean patched installation of the tool:

To install it you must run:

```bash
pipx uninstall flintrock
pipx install flintrock
~/dataengineering-spark/scripts/patch.py
```

### Restarting server

With all the previous installations the system should be ready to start the configuration procedure. To finish this stage, it is required to reboot the system to ensure all changes take effect. To reboot the system, run:
```bash
sudo reboot
```
This will log you out, and you must login again in the same way as before.

## Cluster configuration

### SSH Credentials

To start the cluster configuration we need to pass the **cluster-key.pem** file to the controller machine. You can do this by running:

```bash
ssh -i cluster-key.pem ubuntu@<ip_address> "mkdir dataengineering-spark/credentials/keys"
scp -i cluster-key.pem cluster-key.pem ubuntu@<ip_address>:~/dataengineering-spark/credentials/keys
ssh -i cluster-key.pem ubuntu@<ip_address> "chmod 400 dataengineering-spark/credentials/keys/cluster-key.pem"
```

### AWS User Credentials

> ⚠️ **Important**: The AWS_SESSION_TOKEN changes with each session and must be updated each time you launch the lab

Go to your cluster server and then go to the aws credentials folder with:

```bash
cd dataengineering-spark/credentials/aws
```

Make a copy of the credentials example file with:

```
cp credentials.sh.template credentials.sh
```

In the page where you launched the AWS Academy session, go to **AWS Details** → **Cloud Access** → **AWS CLI** to get the account credentials. With this information, open and complete the **credentials.sh** file with the corresponding information. You should copy the 3 values independently.

## Usage on Cluster Controller Machine

Within the scripts directory in the controller machine, you will find the following relevant scripts:

- `launch.sh` - Deploys the cluster
- `login.sh` - SSH into the master node
- `destroy.sh` - Destroys the cluster

### launch.sh

Uses **config/**, **credentials/**, and **scripts/** to deploy and configure your cluster.

The base configuration has been provided, but you may need to edit `config/flintrock/config.yaml` if you want to:

- Change the instance type (default: **t2.micro**)
- Update the AMI ID
- Modify number of workers (default: 2)

If deployment fails, the script will prompt you about keeping or deleting the created machines.

Expected runtime: 2–4 minutes.

### login.sh

Connects you to the master machine via SSH.

### destroy.sh

Destroys the cluster EC2 instances, but keeps all configurations (S3 bucket, keys, etc.) intact.

You may see residual EC2 security groups named **flintrock** or **flintrock-spark-cluster**. These can be deleted manually.

## Usage on the Cluster Master Machine

The **scripts** directory contains the following commands:

### clean.sh

Goes through each worker and cleans the **~/spark/work** directory to free disk space.

### get_usage.sh

Reports CPU and memory usage for each machine. The first column is the master, followed by each worker.

The script uses a default interval of 5 seconds. You can use an integer parameter to change the refresh interval:

```bash
./get_usage.sh 10
```

That command will report the usage every 10 seconds.

### submit.sh

Wrapper for `spark-submit`. Accepts one parameter: the script to submit.

## Testing

There are two test scripts provided to verify your Spark setup.

### test-000.sh

A simple distributed map-reduce script. The test output can be found at **scripts/test-000.log**. This tests calculate the sum of the first 1 million natural numbers squared. The expected log should report:

```
Sum of squares: 333332833333500000
```

### test-001.sh

> ⚠️ **Important**: Remember to configure the bucket name by editing the line 9 in the **scripts/test-001.py** file accordingly
 
Tests S3 integration and PySpark SQL features, by loading reference data and executing SQL operations.

To run this test it is required to vertically and horizontally scale the cluster. The recommended configuration considers **7** workers with machines type **t2.medium**. This test will generate files to be stored in the S3 bucket you created at the beginning of this tutorial. You must configure the bucket name by editing the line 9 in the **scripts/test-001.py** file.

Once ran, the expected log should report:

```
Reading file vlt_observations_000.csv from paranal-data bucket
Writting file as vlt_observations_000.parsed.parquet into 12345678-k-dde bucket
```

And you should find the following folders in your S3 bucket:

- **vlt_observations_000.parquet**
- **vlt_observations_000.parsed.csv**
- **vlt_observations_000.parsed.parquet**
