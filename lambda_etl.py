# Import standard libraries
import sys
import logging
import json
import os
import boto3

# Import layer libraries
import pandas as pd
import sqlalchemy

# Logger settings
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Create the database connection outside of the handler to allow connections to be re-used by subsequent function invocations.
# RDS settings
user_name = os.environ['USER_NAME']
password = os.environ['PASSWORD']
rds_proxy_host = os.environ['RDS_PROXY_HOST']
db_name = os.environ['DB_NAME']
# Connect to RDS database
try:
    engine = sqlalchemy.create_engine(f'mysql+mysqlconnector://{user_name}:{password}@{rds_proxy_host}:3306/{db_name}')
    print('engine created')
except Exception as e:
    logger.error(e)
    sys.exit(1)

# Create the S3 connection
s3 = boto3.client(service_name='s3')


def lambda_handler(event, context):
    # Read JSON file from S3
    bucket_name = "fnfl2024"
    #file_name = "sleeper/allplayers.json"
    file_name = "sleeper/test_reads3.json"
    try:
        obj = s3.get_object(Bucket=bucket_name, Key=file_name)
        file_contents = json.loads(obj['Body'].read())
    except Exception as err:
        print(err)
    
    # Convert JSON to dataframe
    allplayers = pd.DataFrame.from_dict(file_contents)
    # Transpose dataframe
    allplayers = allplayers.T
    # Create a column for sleeper_id based on the index
    allplayers = allplayers.reset_index(names='id_sleeper')
    # 
    # Select only relevant columns
    allplayers = allplayers[[
        'id_sleeper',
        'full_name', 
        'weight', 'height',
        'birth_date', 'age', 
        'high_school', 'college',
    ]]
    '''
        'sport', 'years_exp', 'active', 'status',
        'team', 'number', 'position', 'fantasy_positions', 'depth_chart_position', 'depth_chart_order',
        'news_updated', 'injury_status', 'injury_body_part', 'injury_start_date', 'injury_notes', 'practice_description', 'practice_participation',
    '''

    # Write the data frame to the RDS
    try:
        allplayers.to_sql(name='test_reads3', con=engine, if_exists = 'replace', index=False)
    except Exception as e:
        logger.error("ERROR: Unexpected error: Could not write to MySQL instance.")
        logger.error(e)
        sys.exit(1)







    
    

    
