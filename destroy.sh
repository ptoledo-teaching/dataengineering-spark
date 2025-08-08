#!/bin/bash
set -e
export PYTHONWARNINGS="ignore"
source credentials/aws/credentials.sh
flintrock --config config/flintrock/config.yaml destroy spark-cluster