from fastapi import FastAPI

app = FastAPI()

@app.get('/')
def read_root():
    root_message = 'Welcome to the Player Predictions API'
    return root_message

@app.get('/player_predictions')
def fetch_player_predictions():
    player_predictions = {
        '1':{
            "franchise_name":"Travis' franchise", "is_user_franchise":"True", "id_sleeper": {
                "3992": {
                    "player_name":"John Smith", "player_position":"QB", "player_team":"HOU", "predictions": {
                        "week_1": {"points_prediction": 12.3}, "week_2": {"points_prediction": 14.2}, "week_3": {"points_prediction": 16.1}
                    }
                }  
            }
        }
    }
    return player_predictions

# Inputs: username, league_id, user_franchise
# Collects: sleeper rosters, RDS players, RDS predictions
# Outputs: franchise_id, franchise_name, is_user_franchise, player_id, player_name, player_position, player_team, week, points_prediction


@app.get('/waiver_wire')
def fetch_waiver_wire():
    waiver_wire = {
        '1':{
            "franchise_name":"Travis' franchise", "is_user_franchise":"True", "id_sleeper": {
                "3992": {
                    "player_name":"John Smith", "player_position":"QB", "player_team":"HOU", "predictions": {
                        "week_1": {"points_prediction": 12.3}, "week_2": {"points_prediction": 14.2}, "week_3": {"points_prediction": 16.1}
                    }
                }  
            }
        },
        '0':{
            "franchise_name":"Free Agent", "is_user_franchise":"False", "id_sleeper": {
                "3993": {
                    "player_name":"Robert Jones", "player_position":"WR", "player_team":"DAL", "predictions": {
                        "week_1": {"points_prediction": 7}, "week_2": {"points_prediction": 10}, "week_3": {"points_prediction": 6.2}
                    }
                }  
            }
        }
    }
    return waiver_wire