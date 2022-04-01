### Design Considerations 
An event driven serverless architecture is chosen to process the client files as it reduces complexity by decomposing the 
workflow and reducing the operational management/cost. They are easily scalable and extensible. 
Also, a serverless architecture promotes workloads that are:

- Reliable: offering your end users a high level of availability. AWS serverless services are reliable because they are also designed for failure.
- Durable: providing storage options that meet the durability needs of your workload.
- Secure: following best practices and using the tools provided to secure access to workloads and limit the blast radius, if any issues occur.
- Performant: using computing resources efficiently and meeting the performance needs of your end users.
- Cost-efficient: designing architectures that avoid unnecessary cost that can scale without overspending, and also be decommissioned, if necessary, without significant overhead.

---

### Event driven architecture of application

![Application architecture](./images/app_architecture.png)

#### Application workflow
1. Client's application writes the required file to client's on premise server s3 mount location (A mount point is an on premise directory to which NFS share is attached).
2. As soon as new file lands in on-premise server mount point location, aws file gateway transfers the file to configured s3 bucket.
3. As the file is created/available in s3 bucket, s3 sends an event to [Lambda function](./lambda_glue_job_trigger.py) with the file details.
4. The above Lambda function starts a [Glue Job](./revenue_glue_job.py) to process the input file.
5. [Glue job](./revenue_glue_job.py) does the required processing to write the final output to S3 bucket. An EventBridge rule triggered if the glue job fails. 
6. Event bridge rule calls a [Lambda function](./lambda_glue_failure_notification.py) to format and publish a failure message to an SNS topic. 
7. [Lambda function](./lambda_glue_failure_notification.py) publishes a failure message to sns topic. All subscribers of sns topic will get the glue job failure notification.

---

### Infrastructure creation
Except for the storage gateway and fileshare, most of the infrastructure setup (AWS Roles, ec2, s3, lambda functions, glue jobs, event bridge, sns topic) needed for this application are created using [cloud formation template](./cf_app_infra.yml). 
As cloud formation does not directly support storage gateway and fileshare they are created and deployed manually following [aws documentation](https://docs.aws.amazon.com/storagegateway/latest/userguide/ec2-gateway-file.html).

1) In aws console search for cloudformation and load the [template](./cf_app_infra.yml) specified in the repository