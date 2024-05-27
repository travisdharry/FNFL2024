# Import standard libraries
import json, boto3, os
# Import layer dependencies
import requests

# Fetch all players from Sleeper
def lambda_handler(event, context):
    # Config
    s3_client = boto3.client('s3')
    
    # Use requests library to fetch all players from Sleeper API
    response = requests.get('https://api.sleeper.app/v1/players/nfl').json()
    
    # Save JSON file to S3
    bucket_name = "fnfl2024"
    file_name = "allplayers.json"
    lambda_path = os.path.join("tmp", file_name)
    s3_path = os.path.join("sleeper", file_name)
    s3_client.put_object(
         Body=json.dumps(response),
         Bucket=bucket_name,
         Key=file_name
    )

    return {
        'statusCode': 200,
        'body': json.dumps('file is created in:'+s3_path)
    }