## Introduction 
An event driven serverless architecture is chosen to process the client files as it reduces complexity by decomposing the 
workflow and reducing the operational management/cost. They are easily scalable and extensible. 
Also a serverless architecture promotes workloads that are:

- Reliable: offering your end users a high level of availability. AWS serverless services are reliable because they are also designed for failure.
- Durable: providing storage options that meet the durability needs of your workload.
- Secure: following best practices and using the tools provided to secure access to workloads and limit the blast radius, if any issues occur.
- Performant: using computing resources efficiently and meeting the performance needs of your end users.
- Cost-efficient: designing architectures that avoid unnecessary cost that can scale without overspending, and also be decommissioned, if necessary, without significant overhead.


### Event drivern Architecture of application

![Application architecture](./images/app_architecture.png)

1. Client's application writes the required file to client's on premise server s3 mount location.
2. As soon as new file lands in on-premise server mount point location (A mount point is a on premise directory to which NFS share is attached), aws file gateway transfers the file
to configured s3 bucket.
3. As the file is created/available in s3 bucket, S3 sends an event to Lambda function with the file details.
4. The above Lambda function starts a Glue Job to process the file 
5. Glue job does the required processing to write the final output to S3 bucket. An EventBridge rule triggered if the glue job fails. 
6. Event bridge rule calls a Lambda function to format and publish a failure message to an SNS topic. 
7. Lambda function publishes a failure message to sns topic. All subscribers of sns topic will get the glue job failure notification.