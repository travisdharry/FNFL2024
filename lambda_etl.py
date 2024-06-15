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
except Exception as e:
    logger.error(e)
    sys.exit(1)
logger.info("RDS connection established")

# Create the S3 connection
s3 = boto3.client(service_name='s3')
logger.info("S3 connection established")

def lambda_handler(event, context):
    ## Extract 
    logger.info("Begin extraction")
    # Read files from S3 using helper functions
    allplayers = read_s3_json("fnfl2024", "sleeper/allplayers.json")
    logger.info("Extracted allplayers.json")
    ids = read_s3_csv("fnfl2024", "lu_ids.csv")
    ourlads = read_s3_csv("fnfl2024", "ourlads.csv")
    sharks = read_s3_csv("fnfl2024", "sharks.csv")
    # Set initial datatypes
    sharks['Week'] = sharks['Week'].astype(str)
    logger.info("Extraction complete")
    
    ## Transform
    # Transpose dataframe
    allplayers = allplayers.T
    # Create a column for sleeper_id based on the index
    allplayers = allplayers.reset_index(names='id_sleeper')
    # Filter out inactive players
    allplayers = allplayers.loc[allplayers['status']!="Inactive"]
    # Create a full name for the Defenses
    allplayers.loc[allplayers['position']=="DEF", 'full_name'] = allplayers.loc[
        allplayers['position']=="DEF", 'first_name'
        ] + " " + allplayers.loc[
            allplayers['position']=="DEF", 'last_name'
            ]
    # Select only relevant columns
    allplayers = allplayers[[
        'id_sleeper',
        'full_name', 
        'weight', 'height',
        'birth_date', 'age', 
        'high_school', 'college',
        'sport', 'years_exp', 'active', 'status',
        'team', 'number', 'position', 'depth_chart_position', 'depth_chart_order',
        'news_updated', 'injury_status', 'injury_body_part', 'injury_start_date', 'injury_notes', 'practice_description', 'practice_participation',
    ]]
    # Set datatypes
    # Convert string columns
    cols_to_string = [
        'id_sleeper',
        'full_name', 
        'high_school', 'college',
        'sport','active', 'status',
        'team', 'number', 'position', 'depth_chart_position', 'depth_chart_order',
        'news_updated', 'injury_status', 'injury_body_part', 'injury_start_date', 'injury_notes', 'practice_description', 'practice_participation'
    ]
    for colName in cols_to_string:
        allplayers[colName] = allplayers[colName].astype(str)
    # Convert float columns
    cols_to_float = [
        'weight', 'height',
        'age', 
        'years_exp',
    ]
    for colName in cols_to_float:
        allplayers[colName] = pd.to_numeric(allplayers[colName], errors='coerce')
        allplayers[colName] = allplayers[colName].astype(float)
    # Convert datetime columns
    cols_to_datetime = [
        'birth_date'
    ]
    for colName in cols_to_datetime:
        allplayers[colName] = pd.to_datetime(allplayers[colName], errors='coerce')
    
    ## Create predictions dataset
    predictions = ids.merge(
        sharks, how='inner', on='id_sharks'
    ).merge(
        ourlads, how = 'left', on='id_ourlads'
    )
    # Clean column names
    predictions = predictions.drop(columns=[
        'id_ourlads', 'id_sharks', '#', 'Tm', 'Opp',
    ])
    # Create a primary key
    predictions['index_predictions'] = predictions['id_sleeper'] + "_" + predictions['Week']
    # Drop NA values
    predictions = predictions.dropna(subset='index_predictions')
    # Drop duplicates
    predictions = predictions.drop_duplicates(subset='index_predictions')
    # Derive additional columns from others
    predictions.loc[predictions['PR']==True, 'pr_yd'] = 13
    predictions.loc[predictions['KR']==True, 'kr_yd'] = 19
    predictions['fgm_yds_over_30'] = predictions['30-39 FGM'] + predictions['40-49 FGM'] + predictions['50+ FGM']
    predictions.loc[(predictions['Pts Agn']<1), 'pts_allow_0'] = 1
    predictions.loc[(predictions['Pts Agn']>=1) & (predictions['Pts Agn']<7), 'pts_allow_1_6'] = 1
    predictions.loc[(predictions['Pts Agn']>=7) & (predictions['Pts Agn']<14), 'pts_allow_7_13'] = 1
    predictions.loc[(predictions['Pts Agn']>=14) & (predictions['Pts Agn']<21), 'pts_allow_14_20'] = 1
    predictions.loc[(predictions['Pts Agn']>=21) & (predictions['Pts Agn']<28), 'pts_allow_21_27'] = 1
    predictions.loc[(predictions['Pts Agn']>=28) & (predictions['Pts Agn']<35), 'pts_allow_28_34'] = 1
    predictions.loc[(predictions['Pts Agn']>=35), 'pts_allow_35p'] = 1
    predictions.loc[(predictions['Yds Allowed']<100), 'yds_allow_0_100'] = 1
    predictions.loc[(predictions['Yds Allowed']>=100) & (predictions['Yds Allowed']<200), 'yds_allow_100_199'] = 1
    predictions.loc[(predictions['Yds Allowed']>=200) & (predictions['Yds Allowed']<300), 'yds_allow_200_299'] = 1
    predictions.loc[(predictions['Yds Allowed']>=400) & (predictions['Yds Allowed']<450), 'yds_allow_400_449'] = 1
    predictions.loc[(predictions['Yds Allowed']>=450) & (predictions['Yds Allowed']<500), 'yds_allow_450_499'] = 1
    predictions.loc[(predictions['Yds Allowed']>=500) & (predictions['Yds Allowed']<550), 'yds_allow_500_549'] = 1
    predictions.loc[(predictions['Yds Allowed']>=550), 'yds_allow_550p'] = 1
    predictions.loc[(predictions['Rsh Yds']>=100) & (predictions['Rsh Yds']<200), 'bonus_rush_yd_100'] = 1
    predictions.loc[predictions['Rsh Yds']>=200, 'bonus_rush_yd_200'] = 1
    predictions.loc[(predictions['Rec Yds']>=100) & (predictions['Rec Yds']<200), 'bonus_rec_yd_100'] = 1
    predictions.loc[predictions['Rec Yds']>=200, 'bonus_rec_yd_200'] = 1
    predictions.loc[(predictions['Pass Yds']>=300) & (predictions['Pass Yds']<400), 'bonus_pass_yd_300'] = 1
    predictions.loc[predictions['Pass Yds']>=400, 'bonus_pass_yd_400'] = 1
    predictions['Rush and Rec Yds'] = predictions['Rsh Yds'] + predictions['Rec Yds']
    predictions.loc[predictions['Rush and Rec Yds']>=200, 'bonus_rush_rec_yd_200'] = 1

    # Rename columns
    predictions = predictions.rename(columns={
        'Week':'week_of_season',
        'Comp':'pass_cmp', 'Pass Yds':'pass_yd', 'Pass TDs':'pass_td', 
        'Int':'pass_int', 
        'Rush':'rush_att', 'Rsh Yds':'rush_yd', 'Rsh TDs':'rush_td', 
        'Fum':'fum_lost',
        'Rec':'rec','Rec Yds':'rec_yd', 'Rec TDs':'rec_td', 
        'XPM':'xpm', 'FGM':'fgm', '10-19 FGM':'fgm_0_19','20-29 FGM':'fgm_20_29', '30-39 FGM':'fgm_30_39', '40-49 FGM':'fgm_40_49', '50+ FGM':'fgm_50p',
        'Miss':'fgmiss', 
        'Scks':'sack', 'DefTD':'def_st_td', 'Safts':'safe',     
    })
    # Drop unnecessary columns which sharks has but sleeper lacks
    predictions = predictions.drop(columns=[
        'Att', '0-9 Pass TDs', '10-19 Pass TDs', '20-29 Pass TDs', '30-39 Pass TDs', '40-49 Pass TDs', '50+ Pass TDs', 'Sck', 
        '0-9 Rsh TDs', '10-19 Rsh TDs', '20-29 Rsh TDs', '30-39 Rsh TDs', '40-49 Rsh TDs', '50+ Rsh TDs',
        '>= 50 yd', '>= 100 yd','0-9 Rec TDs', '10-19 Rec TDs', '20-29 Rec TDs', '30-39 Rec TDs','40-49 Rec TDs', '50+ Rec TDs',
        'Tgt', 'RZ Tgt', 
        'Kick Ret Yds','PR', 'KR',
        'XPA','FGA', 
        'Punts','Punt Yds', 'Punts Inside 20', 
        'Yds Allowed', 'Pts Agn', 
        'Rush and Rec Yds'
    ])
    # Set to zero predictions which sharks lacks but sleeper has
    for colName in [
        'pass_2pt', 'rush_2pt', 'rec_2pt', 'xpmiss', 
        'int', 'fum_rec', 'blk_kick', 'ff','def_st_ff','def_st_fum_rec',
        'def_td','def_3_and_out','def_2pt',
        'st_fum_rec','st_ff','st_td',
        'fum','fum_rec_td',
    ]:
        predictions[colName] = 0
        # Change each column to float64 data type
        predictions[colName] = predictions[colName].astype('float64')
    # Set NA values to zero
    predictions = predictions.fillna(0)
    # Move a couple of the defensive int and fumble scores to the proper column
    defensive_ids = [
        'MIN','KC','DEN','CIN','CHI','TEN','NYG','SF','PHI','BUF','DET','MIA','GB','NO','LAR','JAX','CAR','ATL','CLE','TB','LAC','WAS','DAL','NYJ','LV','SEA','ARI','IND','PIT','BAL','NE','HOU',
    ]
    predictions.loc[predictions['id_sleeper'].isin(defensive_ids), 'int'] = predictions.loc[predictions['id_sleeper'].isin(defensive_ids), 'pass_int']
    predictions.loc[predictions['id_sleeper'].isin(defensive_ids), 'pass_int'] = 0
    predictions.loc[predictions['id_sleeper'].isin(defensive_ids), 'fum'] = predictions.loc[predictions['id_sleeper'].isin(defensive_ids), 'fum_lost']
    predictions.loc[predictions['id_sleeper'].isin(defensive_ids), 'fum_lost'] = 0
    # Tidy up columns
    predictions = predictions[[
        'index_predictions', 'id_sleeper', 'week_of_season', 'pass_cmp', 'pass_yd',
        'pass_td', 'pass_int', 'rush_att', 'rush_yd', 'rush_td', 'fum_lost',
        'rec', 'rec_yd', 'rec_td', 'xpm', 'fgm', 'fgm_0_19', 'fgm_20_29',
        'fgm_30_39', 'fgm_40_49', 'fgm_50p', 'fgmiss', 'sack', 'def_st_td',
        'safe', 'pr_yd', 'kr_yd', 'fgm_yds_over_30', 'pts_allow_0',
        'pts_allow_1_6', 'pts_allow_7_13', 'pts_allow_14_20', 'pts_allow_21_27',
        'pts_allow_28_34', 'pts_allow_35p', 'yds_allow_0_100',
        'yds_allow_100_199', 'yds_allow_200_299', 'yds_allow_400_449',
        'yds_allow_450_499', 'yds_allow_500_549', 'yds_allow_550p',
        'bonus_rush_yd_100', 'bonus_rush_yd_200', 'bonus_rec_yd_100',
        'bonus_rec_yd_200', 'bonus_pass_yd_300', 'bonus_pass_yd_400',
        'bonus_rush_rec_yd_200', 'pass_2pt', 'rush_2pt',
        'rec_2pt', 'xpmiss', 'int', 'fum_rec', 'blk_kick', 'ff', 'def_st_ff',
        'def_st_fum_rec', 'def_td', 'def_3_and_out', 'def_2pt', 'st_fum_rec',
        'st_ff', 'st_td', 'fum', 'fum_rec_td'
    ]]
    # Set predictions datatypes
    # String datatypes
    cols_to_string_predictions = [
        'index_predictions', 'id_sleeper', 'week_of_season',
    ]
    for colName in cols_to_string_predictions:
        predictions[colName] = predictions[colName].astype(str)
    # Float datatypes
    cols_to_float_predictions = [
        'pass_cmp', 'pass_yd',
        'pass_td', 'pass_int', 'rush_att', 'rush_yd', 'rush_td', 'fum_lost',
        'rec', 'rec_yd', 'rec_td', 'xpm', 'fgm', 'fgm_0_19', 'fgm_20_29',
        'fgm_30_39', 'fgm_40_49', 'fgm_50p', 'fgmiss', 'sack', 'def_st_td',
        'safe', 'pr_yd', 'kr_yd', 'fgm_yds_over_30', 'pts_allow_0',
        'pts_allow_1_6', 'pts_allow_7_13', 'pts_allow_14_20', 'pts_allow_21_27',
        'pts_allow_28_34', 'pts_allow_35p', 'yds_allow_0_100',
        'yds_allow_100_199', 'yds_allow_200_299', 'yds_allow_400_449',
        'yds_allow_450_499', 'yds_allow_500_549', 'yds_allow_550p',
        'bonus_rush_yd_100', 'bonus_rush_yd_200', 'bonus_rec_yd_100',
        'bonus_rec_yd_200', 'bonus_pass_yd_300', 'bonus_pass_yd_400',
        'bonus_rush_rec_yd_200', 'pass_2pt', 'rush_2pt',
        'rec_2pt', 'xpmiss', 'int', 'fum_rec', 'blk_kick', 'ff', 'def_st_ff',
        'def_st_fum_rec', 'def_td', 'def_3_and_out', 'def_2pt', 'st_fum_rec',
        'st_ff', 'st_td', 'fum', 'fum_rec_td'
    ]
    for colName in cols_to_float_predictions:
        predictions[colName] = pd.to_numeric(predictions[colName], errors='coerce')
        predictions[colName] = predictions[colName].astype(float)
    logger.info("Transformations complete")
    
    ## Load
    # Write allplayers df to the RDS
    try:
        allplayers.to_sql(name='players', con=engine, if_exists = 'replace', index=False)
        logger.info("Loaded allplayers df to MySQL instance")
    except Exception as e:
        logger.error("ERROR: Unexpected error: Could not write allplayers df to MySQL instance.")
        logger.error(e)
        sys.exit(1)
    # Write predictions df to the RDS
    try:
        predictions.to_sql(name='predictions', con=engine, if_exists = 'replace', index=False)
        logger.info("Loaded predictions df to MySQL instance")
    except Exception as e:
        logger.error("ERROR: Unexpected error: Could not write predictions df to MySQL instance.")
        logger.error(e)
        sys.exit(1)
    logger.info("Loading complete")
    




### Helper functions
def read_s3_json(bucket_name, file_name):
    try:
        # Get file from s3
        object = s3.get_object(Bucket=bucket_name, Key=file_name)
        # Convert file to JSON object
        file_contents = json.loads(object['Body'].read())
        # Convert JSON to dataframe
        df = pd.DataFrame.from_dict(file_contents)
    except Exception as err:
        print(err)
        df = None
    return df

def read_s3_csv(bucket_name, file_name):
    try:
        # Get file from s3
        object = s3.get_object(Bucket=bucket_name, Key=file_name)
        # Convert CSV to dataframe
        df = pd.read_csv(object['Body'], sep=',')
    except Exception as err:
        print(err)
        df = None
    return df


    

    
