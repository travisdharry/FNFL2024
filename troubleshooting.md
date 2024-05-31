# Troubleshooting

## Lambda call Sleeper API and save to S3 bucket
### Trigger: Cron job
### Networking
### Permissions
### Function


## Lambda write to RDS
### Trigger: S3 Put
### Networking
- Need to create a RDS proxy endpoint because Lambda functions which are elastic can quickly overwhelm an RDS server with limited elasticity. The proxy endpoint throttles the Lambda requests to RDS.
### Permissions
- Needs LambdaExecution Role
### Function


## Lambda on a VPC to read S3
### Trigger: S3 Put
### Networking
- Need a S3-specific Gateway endpoint set up in the VPC so that it can securely connect to S3.
### Permissions
- Ensure that the Lambda's security group allows outgoing HTTPS traffic to either the internet (0.0.0.0/0) or to the prefix list ID (pl-xxxxxxx) for S3 in your region.
### Function


