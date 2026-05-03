import os
import shutil
import subprocess
import tarfile
import tempfile

from pyspark.sql import SparkSession
from pyspark.sql.functions import expr, monotonically_increasing_id
from pyspark.sql.types import StringType, StructField, StructType

# Buckets
# You must create an s3 bucket in your aws account with the name XXXXXXXX-X-spark-data
# where XXXXXXXX-X is your rut without dots. E.G. 12.345.678-K => 12345678-K-spark-data
# You must replace the XXXXXXXX-X in the following line
user_bucket = "XXXXXXXX-X-spark-data"
source_bucket = "dataengineering-datasets"
source_key = "eso-archive/observations.2025.csv.tar.gz"


def run_command(command):
    subprocess.run(command, check=True)


def s3_object_exists(bucket_name, object_key):
    result = subprocess.run(
        [
            "aws",
            "s3api",
            "head-object",
            "--bucket",
            bucket_name,
            "--key",
            object_key,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def resolve_dataset_paths(source_path):
    if source_path.endswith(".csv.tar.gz"):
        return {
            "source_is_archive": True,
            "csv_key": source_path[:-7],
            "dataset_key": source_path[:-11],
        }

    if source_path.endswith(".tar.gz"):
        csv_key = source_path[:-7]
        dataset_key = csv_key[:-4] if csv_key.endswith(".csv") else csv_key
        return {
            "source_is_archive": True,
            "csv_key": csv_key,
            "dataset_key": dataset_key,
        }

    if source_path.endswith(".csv"):
        return {
            "source_is_archive": False,
            "csv_key": source_path,
            "dataset_key": source_path[:-4],
        }

    return {
        "source_is_archive": False,
        "csv_key": f"{source_path}.csv",
        "dataset_key": source_path,
    }


def cache_csv_from_archive(source_bucket_name, source_archive_key, target_bucket_name, cached_csv_key):
    with tempfile.TemporaryDirectory(prefix="spark-input-") as temp_dir:
        local_archive_path = os.path.join(temp_dir, "dataset.tar.gz")

        print(f"Downloading archive s3://{source_bucket_name}/{source_archive_key}")
        run_command([
            "aws",
            "s3",
            "cp",
            "--no-progress",
            "--no-sign-request",
            f"s3://{source_bucket_name}/{source_archive_key}",
            local_archive_path,
        ])

        with tarfile.open(local_archive_path, "r:gz") as archive:
            csv_members = [
                member for member in archive.getmembers()
                if member.isfile() and member.name.endswith(".csv")
            ]

            if len(csv_members) != 1:
                raise RuntimeError(
                    f"Expected exactly one CSV file in {source_archive_key}, found {len(csv_members)}."
                )

            csv_member = csv_members[0]
            local_csv_path = os.path.join(temp_dir, os.path.basename(csv_member.name))
            extracted_csv = archive.extractfile(csv_member)
            if extracted_csv is None:
                raise RuntimeError(f"Could not extract {csv_member.name} from {source_archive_key}.")

            with extracted_csv, open(local_csv_path, "wb") as output_file:
                shutil.copyfileobj(extracted_csv, output_file)

        print(f"Uploading extracted CSV to s3://{target_bucket_name}/{cached_csv_key}")
        run_command([
            "aws",
            "s3",
            "cp",
            "--no-progress",
            local_csv_path,
            f"s3://{target_bucket_name}/{cached_csv_key}",
        ])


paths = resolve_dataset_paths(source_key)
csv_key = paths["csv_key"]
dataset_key = paths["dataset_key"]
cached_csv_key = None

if paths["source_is_archive"]:
    cached_csv_key = f"csv/{csv_key}"
    input_csv_path = f"s3a://{user_bucket}/{cached_csv_key}"
else:
    input_csv_path = f"s3a://{source_bucket}/{csv_key}"

# Create a SparkSession
spark = SparkSession.builder.getOrCreate()

# Create the data schema
schema = StructType([
    StructField("object", StringType(), True),
    StructField("right_ascension", StringType(), True),
    StructField("declination", StringType(), True),
    StructField("obs_timestamp", StringType(), True),
    StructField("program_id", StringType(), True),
    StructField("investigators", StringType(), True),
    StructField("obs_mode", StringType(), True),
    StructField("title", StringType(), True),
    StructField("program_type", StringType(), True),
    StructField("instrument", StringType(), True),
    StructField("category", StringType(), True),
    StructField("obs_type", StringType(), True),
    StructField("obs_nature", StringType(), True),
    StructField("dataset_id", StringType(), True),
    StructField("obs_file", StringType(), True),
    StructField("release_date", StringType(), True),
    StructField("obs_name", StringType(), True),
    StructField("obs_id", StringType(), True),
    StructField("template_id", StringType(), True),
    StructField("template_start", StringType(), True),
    StructField("exposition_time", StringType(), True),
    StructField("filter_lambda_min", StringType(), True),
    StructField("filter_lambda_max", StringType(), True),
    StructField("filter", StringType(), True),
    StructField("grism", StringType(), True),
    StructField("grating", StringType(), True),
    StructField("slit", StringType(), True),
    StructField("obs_mjd", StringType(), True),
    StructField("airmass", StringType(), True),
    StructField("seeing", StringType(), True),
    StructField("distance", StringType(), True),
    StructField("position", StringType(), True)
])

float_columns = [
    "exposition_time",
    "filter_lambda_min",
    "filter_lambda_max",
    "obs_mjd",
    "airmass",
    "seeing",
]

try:
    if paths["source_is_archive"]:
        if s3_object_exists(user_bucket, cached_csv_key):
            print(f"Using cached CSV s3://{user_bucket}/{cached_csv_key}")
        else:
            cache_csv_from_archive(source_bucket, source_key, user_bucket, cached_csv_key)

    # Read the CSV file and number the rows
    if paths["source_is_archive"]:
        print(f"Reading extracted file {csv_key} from {user_bucket} bucket")
    else:
        print(f"Reading file {csv_key} from {source_bucket} bucket")

    df_0 = spark.read.csv(input_csv_path, header=False, schema=schema)
    print(f"    - {df_0.count()} rows read")
    print("    - Creating row number column")
    df_0 = df_0.withColumn("oid", monotonically_increasing_id())

    print(f"Writing file as {dataset_key}.parquet into {user_bucket} bucket")
    # Store the data in user bucket
    df_0.write.mode("overwrite").parquet(f"s3a://{user_bucket}/{dataset_key}.parquet")

    # Read the data and parse floats
    print(f"Reading file {dataset_key}.parquet from {user_bucket} bucket")
    df_1 = spark.read.parquet(f"s3a://{user_bucket}/{dataset_key}.parquet")
    print(f"    - {df_1.count()} rows read")
    print("    - Parsing float columns with tolerant cast")
    for column_name in float_columns:
        df_1 = df_1.withColumn(column_name, expr(f"try_cast(`{column_name}` as float)"))

    # Store the data in user bucket
    print(f"Writing file as {dataset_key}.parsed.csv into {user_bucket} bucket")
    df_1.write.mode("overwrite").csv(f"s3a://{user_bucket}/{dataset_key}.parsed.csv")
    print(f"Writing file as {dataset_key}.parsed.parquet into {user_bucket} bucket")
    df_1.write.mode("overwrite").parquet(f"s3a://{user_bucket}/{dataset_key}.parsed.parquet")
finally:
    # Stop Spark session
    spark.stop()
