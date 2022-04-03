import boto3
import json
import urllib.parse
import boto3

print('Loading function')


def lambda_handler(_event, _context):
    glue = boto3.client('glue')
    gluejobname = "adobe_exercise_glue_job"

    # extracting the bucket and key details of input filw
    bucket = _event['Records'][0]['s3']['bucket']['name']
    key = urllib.parse.unquote_plus(_event['Records'][0]['s3']['object']['key'], encoding='utf-8')
    try:
        print("printing bucket")
        print(bucket)
        print(key)
        # triggering the glue job
        runId = glue.start_job_run(JobName=gluejobname, Arguments={'--s3_bucket': bucket, '--s3_key': key})
        status = glue.get_job_run(JobName=gluejobname, RunId=runId['JobRunId'])
        print("Job Status : ", status['JobRun']['JobRunState'])
    except Exception as e:
        print(e)
        raise
