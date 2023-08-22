# conftest.py
import os
import boto3
import moto
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.types import *

@pytest.fixture(scope="function")
def moto_s3():
    with moto.mock_s3():
        s3 = boto3.resource("s3", region_name="us-east-1")
        s3.create_bucket(
            Bucket="mybucket",
        )
        object = s3.Object(
            "mybucket",
            "test-vehichle-01/this/_flir_adk_rgb_front_right_image_raw_resized_1280_720_post_obj_dets/all_predictions.csv",
        )
        object2 = s3.Object(
            "mybucket",
            "test-vehichle-01/this/_flir_adk_rgb_front_right_image_raw_resized_1280_720_post_lane_dets/lanes.csv"
        )
        data = b"Here we have some data"
        object.put(Body=data)
        object2.put(Body=data)
        yield s3


@pytest.fixture(scope="function")
def moto_dynamodb():
    with moto.mock_dynamodb():
        dynamodb = boto3.resource("dynamodb")
        dynamodb.create_table(
            TableName="mytable",
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "N"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield dynamodb


@pytest.fixture(scope="session")
def spark():
    os.environ["PYSPARK_SUBMIT_ARGS"] = (
    '--packages "org.apache.hadoop:hadoop-aws:3.3.1" pyspark-shell'
    )
    spark = SparkSession.builder.getOrCreate()

    # Setup spark to use s3, and point it to the moto server.
    hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
    hadoop_conf.set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    hadoop_conf.set("fs.s3a.access.key", "mock")
    hadoop_conf.set("fs.s3a.secret.key", "mock")
    hadoop_conf.set("fs.s3a.endpoint", "http://127.0.0.1:5000")
    yield spark 
    spark.stop()
