# AWS Process
### References:
GokceDB-1: https://www.youtube.com/watch?v=Z3dMhPxbuG0
AWSTutorial-1: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-lambda-tutorial.html

## VPC
Creation:
Follow GokceDB-1 with the following exceptions:
- Had a problem with RDS unable to deply without having 2+ Availability Zones, so set up 2 Availability Zones with 1 Nat Gateway per zone
- In 'VPC endpoints' select "S3 Gateway"
Security Group
- Allow HTTP and HTTPS outbound traffic to anywhere

## Scraping Lambda
Creation:
- Default settings
Setup:
- Assign layer for requests
- Change timeout to 10s
Trigger:
- Add trigger of type "EventBridge (CloudWatch Events)"
- Create rule for scheduled cron job
`cron(0 08 * * ? *)`
Permissions:
- Configure Execution Role
- Add permissions: "AmazonS3FullAccess"
Deployment:
- Paste code in from file

## RDS - MySQL
Creation:
- Free tier
- Set username & passwords
- Assign to VPC
- In 'Additional Configuration' specify database name
Wait a few minutes until it becomes "Available"

## ETL Lambda
Creation:
- Create from within the RDS Database "Actions" menu
- Select "Connect using RDS Proxy"
Execution Role:
- Open IAM "Roles" menu, select "Create Role"
- Specify 'Trusted Entity Type'=="AWS Service" and 'Use Case'=="Lambda"
- Add permissions policies: ["AmazonS3FullAccess", "AWSLambdaBasicExecutionRole", "AWSLambdaExecute", "AWSLambdaVPCAccessExecutionRole"]
- Copy the ARN for the role
S3 VPC Endpoint:
- In VPC Console 'Endpoints' create endpoint
- In Services select the S3 option that is of "Gateway" type
- Select the VPC
- Select "Public" subnet
S3 VPC Security Group
- In VPC Console 'Security Groups' create a new security group called something like "s3-outbound"
- Set Outbound rule destination to the S3 option with a "pl-XXXXXX" preface
- In Lambda/Configuration/VPC edit the security groups
- Add the S3 Outbound rule to the Lambda's security group
- The Lambda should show two outbound rules - one for the RDS Proxy and one for the S3 bucket
Setup:
- Change runtime to Python 
- Change handler to "lambda_function.lambda_handler"
- Replace old .js code file with a "lambda_function.py" file 
- Paste code from file
- In 'Configuration' set memory to 512 and timeout to 1m15s
- In 'Configuration' set Execution role to the ARN from previous step
- In 'Configuration' set environment variables for USER_NAME, DB_NAME, PASSWORD, and RDS_PROXY_HOST (should be something like "proxy-XXXXXXXXXXXXX-DBNAME.proxy-XXXXXXXXXXXX.us-east-2.rds.amazonaws.com" - You can find it in RDS/Proxies/PROXYID 'Proxy endpoints')
- Edit test event
- Add layers for pandas and sqlalchemy
Trigger
- Create S3 trigger
- Specify bucket
- 'Event type' == "PUT"
- Set prefix/suffix






## Backend API Lambda
Creation:
- Enable Function URL
- Enable VPC
- Select private subnet
- Select security group from VPC creation step to allow outbound traffic
Setup:
- Assign layers for pandas, sqlalchemy, and requests
- Change handler to main.handler
- Set test code
- Change timeout to 1m
- In 'Configuration' set environment variables for USER_NAME, DB_NAME, PASSWORD, and RDS_PROXY_HOST (should be something like "proxy-XXXXXXXXXXXXX-DBNAME.proxy-XXXXXXXXXXXX.us-east-2.rds.amazonaws.com" - You can find it in RDS/Proxies/PROXYID 'Proxy endpoints')
- In Configuration/VPC select 'Edit' then attach lambda-rdsproxy-X security group
Deployment:
- Install all dependencies in the same folder as script. Then zip them all together. You have to specify the x86_64 architecture so pip installs the version of the dependency that will work with the Lambda function.
` pip install -r requirements.txt --platform manylinux2014_x86_64 --target ./python --only-binary=:all: `
` (cd python; zip ../lambda_function.zip -r .) `
`zip lambda_function.zip -u main.py`
- Upload zip file to S3
- Upload zip file to Lambda from S3


