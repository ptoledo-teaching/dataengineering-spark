#!/bin/bash
source credentials/aws/credentials.sh
flintrock --config config/flintrock/config.yaml login spark-cluster 2>/dev/null