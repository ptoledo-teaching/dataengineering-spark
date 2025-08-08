#!/bin/bash
set -e
source credentials/aws/credentials.sh
flintrock --config config/flintrock/config.yaml login spark-cluster