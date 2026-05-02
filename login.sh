#!/bin/bash
SPARK_DIR=/opt/dataengineering-spark
source $SPARK_DIR/credentials/aws/credentials.sh
flintrock --config $SPARK_DIR/config/flintrock/config.yaml login spark-cluster 2>/dev/null