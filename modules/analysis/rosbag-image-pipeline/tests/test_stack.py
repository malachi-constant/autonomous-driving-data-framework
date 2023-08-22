from pyspark.sql.types import *
import os
from image_dags import detect_scenes
from image_dags.detect_scenes import *
import subprocess


def test_get_batch_file_metadata(moto_dynamodb):
    dynamodb = boto3.resource("dynamodb")
    table_name = "mytable"
    table = dynamodb.Table(table_name)
    items = [{"pk": 1}, {"pk": 2}]
    for item in items:
        table.put_item(Item=item)
    for item in items:
        result = get_batch_file_metadata(table_name, item["pk"], "us-east-1")
        assert len(result) > 0


def test_detect_scenes_parse_arguments():
    args = parse_arguments(
        [
            "--batch-metadata-table-name",
            "dummy",
            "--batch-id",
            "dummy",
            "--input-bucket",
            "mybucket",
            "--output-bucket",
            "mybucket",
            "--output-dynamo-table",
            "mytable",
            "--region",
            "us-east-1",
        ]
    )
    assert args.batch_metadata_table_name == "dummy"
    assert args.batch_id == "dummy"
    assert args.input_bucket == "mybucket"
    assert args.output_bucket == "mybucket"
    assert args.output_dynamo_table == "mytable"
    assert args.region == "us-east-1"

def test_load_lane_detection():
    # start moto server, by default it runs on localhost on port 5000.
    process = subprocess.Popen(
        "moto_server s3", stdout=subprocess.PIPE,
        shell=True, preexec_fn=os.setsid
    )
    # create an s3 connection that points to the moto server. 
    s3_conn = boto3.resource(
        "s3", endpoint_url="http://127.0.0.1:5000"
    )
    # create an S3 bucket.
    s3_conn.create_bucket(Bucket="bucket")
    # configure pyspark to use hadoop-aws module.
    # notice that we reference the hadoop version we installed.
    os.environ[
        "PYSPARK_SUBMIT_ARGS"
    ] = '--packages "org.apache.hadoop:hadoop-aws:2.7.3" pyspark-shell'
    # get the spark session object and hadoop configuration.
    spark = SparkSession.builder.getOrCreate()
    hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
    # mock the aws credentials to access s3.
    hadoop_conf.set("fs.s3a.access.key", "dummy-value")
    hadoop_conf.set("fs.s3a.secret.key", "dummy-value")
    # we point s3a to our moto server.
    hadoop_conf.set("fs.s3a.endpoint", "http://127.0.0.1:5000")
    # we need to configure hadoop to use s3a.
    hadoop_conf.set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    sample_metadata = [{"raw_image_bucket": "mybucket", "drive_id": "test-vehichle-01", "file_id": "this.jpg", 's3_key': 'test-vehichle-01/this/_flir_adk_rgb_front_right_image_raw_resized_/1280_720_post_lane_dets/lanes.csv'}]
    load_lane_detection(spark, sample_metadata)

# def test_detect_scenes_load_obj_detection(moto_s3):
#     detect_scenes.obj_schema = StructType(
#         [
#             StructField("_c0", IntegerType(), True),
#             StructField("xmin", DoubleType(), True),
#             StructField("ymin", DoubleType(), True),
#             StructField("xmax", DoubleType(), True),
#             StructField("ymax", DoubleType(), True),
#             StructField("confidence", DoubleType(), True),
#             StructField("class", IntegerType(), True),
#             StructField("name", StringType(), True),
#             StructField("source_image", StringType(), True),
#         ]
#     )
#     import os
#     os.environ["PYSPARK_SUBMIT_ARGS"] = (
#     '--packages "org.apache.hadoop:hadoop-aws:3.3.1" pyspark-shell'
#     )
#     spark = SparkSession.builder.getOrCreate()

#     # Setup spark to use s3, and point it to the moto server.
#     hadoop_conf = spark.sparkContext._jsc.hadoopConfiguration()
#     hadoop_conf.set("fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
#     hadoop_conf.set("fs.s3a.access.key", "mock")
#     hadoop_conf.set("fs.s3a.secret.key", "mock")
#     hadoop_conf.set("fs.s3a.endpoint", "http://127.0.0.1:5000")
#     sample_metadata = [{"raw_image_bucket": "mybucket", "drive_id": "test-vehichle-01", "file_id": "this.jpg"}]
#     results = load_obj_detection(spark, batch_metadata=sample_metadata)
#     print(results)
