from fastapi import FastAPI
from mangum import Mangum
from sleeperpy import User, Leagues
import pandas as pd
import sys
import logging
import os
import json
import sqlalchemy
import requests

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

app = FastAPI()
handler = Mangum(app)

@app.get('/')
def read_root():
    root_message = 'Welcome to the Player Predictions API'
    return root_message

# Waiver wire
# Inputs: userid, league_id
# Collects: sleeper rosters, RDS players, RDS predictions
# Outputs: franchise_id, franchise_name, is_user_franchise, player_id, player_name, player_position, player_team, week, points_prediction
@app.get('/waiver_wire/{user_id}/{league_id}')
def fetch_waiver_wire(user_id: str, league_id: str):
    if user_id and league_id:
        logger.info("Connecting to Sleeper")
        # Receive user ID & league ID in GET request, then fetch league data from Sleeper API
        selected_league = Leagues.get_league(league_id)
        logger.info("Connected to Sleeper once")
        scoring_settings = selected_league['scoring_settings']
        # Get the rosters for the league
        rosters = Leagues.get_rosters(league_id)
        users = Leagues.get_users(league_id)

        # Bring in the franchise_id for each roster
        roster_df = pd.DataFrame(rosters)
        roster_df = roster_df[['players', 'owner_id']]
        # Explode the roster_df to get a row for each player on each roster
        roster_df = roster_df.explode('players')
        roster_df['players'] = roster_df['players'].astype(str)
        roster_df = roster_df.rename(columns={'players': 'id_sleeper'})

        # Get info about each franchise
        franchises = pd.DataFrame()
        franchises['owner_id'] = [x['user_id'] for x in users]
        franchises['owner_name'] = [x['display_name'] for x in users]
        franchises['team_name'] = [x['metadata']['team_name'] if 'team_name' in x['metadata'] else x['display_name'] for x in users]
        # Create a True/False column for whether the owner is the user
        franchises['is_user'] = False
        franchises.loc[franchises['owner_id'] == user_id, 'is_user'] = True

        # Merge roster_df with franchises to get the owner_name and team_name for each player
        roster_df = pd.merge(roster_df, franchises, on='owner_id')

        logger.info("Connecting to RDS")
        # Query the RDS database
        players = pd.read_sql(
            '''
            SELECT id_sleeper, full_name, age, team, number, position 
            FROM players
            ''',
            con=engine
        )
        predictions = pd.read_sql(
            '''
            SELECT * from predictions
            ''',
            con=engine
        )
        logger.info("Performing transformations on database results")
        # Get a list of rostered players 
        rostered_players = roster_df['id_sleeper'].tolist()
        # Get a list of the user's players
        user_players = roster_df.loc[roster_df['is_user'] == True, 'id_sleeper'].tolist()
        # Filter the predictions to only include players on the user's roster or on waivers
        predictions = predictions.loc[(~predictions['id_sleeper'].isin(rostered_players)) | (predictions['id_sleeper'].isin(user_players))]
        predictions = predictions.merge(players, on='id_sleeper', how='left')

        # Multiply each prediction column by the corresponding scoring setting
        for column in predictions.columns:
            if column in scoring_settings:
                predictions[column] = predictions[column] * scoring_settings[column]
        # Sum up the total points for each column in the scoring settings
        predictions['predicted_fantasy_points'] = predictions[list(scoring_settings.keys())].sum(axis=1)
        predictions = predictions.drop(columns=list(scoring_settings.keys())).drop(columns=['index_predictions'])
        predictions.sort_values(by='predicted_fantasy_points', ascending=False, inplace=True, ignore_index=True)
        predictions = predictions[['id_sleeper', 'full_name', 'age', 'team', 'number', 'position', 'week_of_season', 'predicted_fantasy_points']]

        # Merge the predictions with the roster_df to get the owner_name and team_name for each player
        complete = pd.merge(predictions, roster_df, on='id_sleeper', how='left')
        # Mark the unrostered players as 'Free Agents'
        complete.loc[complete['owner_id'].isnull(), 'team_name'] = 'Free Agents'
        complete.loc[complete['owner_id'].isnull(), 'owner_name'] = 'Free Agents'
        complete = complete.fillna("")
        complete = complete.drop_duplicates(subset=['id_sleeper', 'week_of_season'], keep='first', ignore_index=True)

        # Convert the dataframe to json
        logger.info("Returning results")
        waiverwire_result = complete.to_dict(orient='records')
        

    return waiverwire_result


# Franchise Comparison
# Inputs: userid, league_id
# Collects: sleeper rosters, RDS players, RDS predictions
# Outputs: franchise_id, franchise_name, is_user_franchise, player_id, player_name, player_position, player_team, week, points_prediction
@app.get('/franchise_comparison/{user_id}/{league_id}')
def fetch_waiver_wire(user_id: str, league_id: str):
    if user_id and league_id:
        logger.info("Connecting to Sleeper")
        # Receive user ID & league ID in GET request, then fetch league data from Sleeper API
        selected_league = Leagues.get_league(league_id)
        logger.info("Connected to Sleeper once")
        roster_positions = selected_league['roster_positions']
        scoring_settings = selected_league['scoring_settings']
        # Get the rosters for the league
        rosters = Leagues.get_rosters(league_id)
        users = Leagues.get_users(league_id)

        # Bring in the franchise_id for each roster
        roster_df = pd.DataFrame(rosters)
        roster_df = roster_df[['players', 'owner_id']]
        # Explode the roster_df to get a row for each player on each roster
        roster_df = roster_df.explode('players')
        roster_df['players'] = roster_df['players'].astype(str)
        roster_df = roster_df.rename(columns={'players': 'id_sleeper'})

        # Get info about each franchise
        franchises = pd.DataFrame()
        franchises['owner_id'] = [x['user_id'] for x in users]
        franchises['owner_name'] = [x['display_name'] for x in users]
        franchises['team_name'] = [x['metadata']['team_name'] if 'team_name' in x['metadata'] else x['display_name'] for x in users]
        # Create a True/False column for whether the owner is the user
        franchises['is_user'] = False
        franchises.loc[franchises['owner_id'] == user_id, 'is_user'] = True

        # Merge roster_df with franchises to get the owner_name and team_name for each player
        roster_df = pd.merge(roster_df, franchises, on='owner_id')

        logger.info("Connecting to RDS")
        # Query the RDS database
        players = pd.read_sql(
            '''
            SELECT id_sleeper, full_name, age, team, number, position 
            FROM players
            ''',
            con=engine
        )
        logger.info(f"Length of players Point1: {len(players)}")
        predictions = pd.read_sql(
            '''
            SELECT * from predictions
            ''',
            con=engine
        )
        logger.info(f"Length of predictions Point2: {len(predictions)}")
        logger.info("Performing transformations on database results")
        # Get a list of rostered players 
        rostered_players = roster_df['id_sleeper'].tolist()
        # Filter the predictions to only include players on the user's roster or on waivers
        predictions = predictions.loc[predictions['id_sleeper'].isin(rostered_players)]
        logger.info(f"Length of predictions Point3: {len(predictions)}")
        predictions = predictions.merge(players, on='id_sleeper', how='left')
        logger.info(f"Length of predictions Point4: {len(predictions)}")

        # Multiply each prediction column by the corresponding scoring setting
        for column in predictions.columns:
            if column in scoring_settings:
                predictions[column] = predictions[column] * scoring_settings[column]
        # Sum up the total points for each column in the scoring settings
        predictions['predicted_fantasy_points'] = predictions[list(scoring_settings.keys())].sum(axis=1)
        predictions = predictions.drop(columns=list(scoring_settings.keys())).drop(columns=['index_predictions'])
        predictions.sort_values(by='predicted_fantasy_points', ascending=False, inplace=True, ignore_index=True)
        predictions = predictions[['id_sleeper', 'full_name', 'age', 'team', 'number', 'position', 'week_of_season', 'predicted_fantasy_points']]

        # Merge the predictions with the roster_df to get the owner_name and team_name for each player
        franchise_comparison = pd.merge(predictions, roster_df, on='id_sleeper', how='left')
        logger.info(f"Length of franchise_comparison Point1: {len(franchise_comparison)}")
 
        # Find which players have any value
        # Initialize a dictionary describing each of the roster positions
        rosterDict = {
            'QB':['QB'], 
            'RB':['RB'],
            'WR':['WR'],
            'TE':['TE'],
            'K':['K'],
            'DEF':['DEF'],
            'FLEX':['RB', 'WR', 'TE'],
            'SUPER_FLEX':['QB', 'RB', 'WR', 'TE'],
        }

        # Mark players who would be started in the roster_position with a "starter" column, initialize as False
        franchise_comparison['starter'] = False
        # Loop through roster positions
        for roster_position in roster_positions:
            # Check that the roster_position is not "BN"
            if roster_position != "BN":
                # Loop through each week of the season
                for week in franchise_comparison['week_of_season'].unique():
                    # Loop through the franchises
                    for franchise in franchise_comparison['owner_name'].unique():
                        # Get the players for the current franchise, week, and roster position
                        players = franchise_comparison[(franchise_comparison['starter'] == False) & (franchise_comparison['owner_name'] == franchise) & (franchise_comparison['week_of_season'] == week) & (franchise_comparison['position'].isin(rosterDict[roster_position]))]
                        # Check that the number of players is greater than 0
                        if len(players) > 0:
                            # Get the player with the highest predicted fantasy points
                            max_player = players.loc[players['predicted_fantasy_points'].idxmax()]
                            # Mark the player as a starter
                            franchise_comparison.loc[max_player.name, 'starter'] = True

        # Fill na values
        franchise_comparison = franchise_comparison.fillna("")
        # Filter out players who are starters
        franchise_comparison = franchise_comparison[franchise_comparison['starter'] == True]
        # Drop duplicates
        logger.info(f"Length of franchise_comparison Point2: {len(franchise_comparison)}")
        franchise_comparison = franchise_comparison.drop_duplicates(subset=['id_sleeper', 'week_of_season'], keep='first', ignore_index=True)
        logger.info(f"Length of franchise_comparison Point3: {len(franchise_comparison)}")

        # Convert the dataframe to json
        logger.info("Returning results")
        franchise_comparison_result = franchise_comparison.to_dict(orient='records')
        

    return franchise_comparison_result