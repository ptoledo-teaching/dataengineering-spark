#!/bin/bash
SPARK_DIR=/opt/dataengineering-spark
source $SPARK_DIR/credentials/aws/credentials.sh
flintrock --config $SPARK_DIR/config/flintrock/config.yaml destroy spark-cluster 2>/dev/null