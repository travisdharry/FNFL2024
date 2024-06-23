# Import dependencies
import json
import requests
import pandas as pd
from flask import Flask, redirect, request, url_for, render_template, session
from sleeperpy import User, Leagues
import plotly
import plotly.express as px
import plotly.graph_objects as go

# Initialize app
app = Flask(__name__)
app.secret_key = 'temporarysecretkey'


# Define routes
# Get the user's username
@app.route('/')
def getUsername():
    return render_template("index.html")

# Set the session variable for user_id
@app.route("/usernameCallback", methods=['GET', 'POST'])
def usernameCallback():
    username = request.form["username"]
    user_id = User.get_user(username)['user_id']
    session['user_id'] = user_id
    return redirect(url_for("getLeague"))

# Have the user select which of their leagues they want to look at
@app.route('/getLeague', methods=['GET', 'POST'])
def getLeague():
    user_id = session.get("user_id")
    leagues = Leagues.get_all_leagues(user_id, 'nfl', 2024)
    league_list = [x['name'] for x in leagues]
    return render_template("getLeague.html", league_list=league_list)

# Set the session variable for the league_id
@app.route("/getLeague/getLeagueCallback", methods=['GET', 'POST'])
def getLeagueCallback():
    league_name = request.form["LeagueName"]
    user_id = session.get("user_id")
    leagues = Leagues.get_all_leagues(user_id, 'nfl', 2024)
    league_id = [x['league_id'] for x in leagues if x['name'] == league_name][0]
    session['league_id'] = league_id
    return redirect(url_for("viewSelector"))

# Have the user select which view they want to see
@app.route('/viewSelector', methods=['GET', 'POST'])
def viewSelector():
    return render_template("viewSelector.html")


# Get the user's roster and all Free Agents
@app.route('/waiver_wire')
def waiver_wire():
    user_id = session.get("user_id")
    league_id = session.get("league_id")
    # Fetch data from backend API
    backendapi_waiverwire_url = f'https://ygn5at2pt5zgycacip4t6kvrey0ayfrl.lambda-url.us-east-2.on.aws//waiver_wire/{user_id}/{league_id}'
    response = requests.get(backendapi_waiverwire_url).json()
    # Parse the data
    waivers = pd.DataFrame(response)
    # Aggregate the data
    waiver_wire = waivers.groupby(['id_sleeper', 'team_name', 'full_name', 'age', 'team', 'number', 'position'])['predicted_fantasy_points'].sum().to_frame().reset_index()
    waiver_wire['predicted_fantasy_points'] = waiver_wire['predicted_fantasy_points'].round(2)
    waiver_wire = waiver_wire.drop(columns=['id_sleeper'])
    waiver_wire = waiver_wire.sort_values('predicted_fantasy_points', ascending=False, ignore_index=True)
    return render_template("waiverWire.html", tables=[waiver_wire.to_html(classes='data')], titles=waiver_wire.columns.values)

# Get a bar chart of player values by franchise
@app.route('/franchise_comparison')
def franchise_comparison():
    user_id = session.get("user_id")
    league_id = session.get("league_id")
    # Fetch data from backend API
    backendapi_franchisecomparison_url = f'https://ygn5at2pt5zgycacip4t6kvrey0ayfrl.lambda-url.us-east-2.on.aws//franchise_comparison/{user_id}/{league_id}'
    response = requests.get(backendapi_franchisecomparison_url)
    # Parse the data
    response_json = response.json()
    backend_response = pd.DataFrame(response_json)
    # Set datatypes
    backend_response['id_sleeper'] = backend_response['id_sleeper'].astype(str)
    backend_response['team_name'] = backend_response['team_name'].astype(str)

    # Aggregate the predicted points
    player_sums = backend_response.groupby(['id_sleeper'])['predicted_fantasy_points'].sum().to_frame().reset_index()
    total_franchise_values = backend_response.groupby('team_name')['predicted_fantasy_points'].sum().round(0).to_frame().reset_index()
    # Merge back in the player info
    player_info = backend_response.drop(columns=['predicted_fantasy_points', 'week_of_season']).drop_duplicates(ignore_index=True)
    franchise_comparisons = player_sums.merge(player_info, on='id_sleeper', how='left')
    # Visualize the data
    fig = px.bar(franchise_comparisons, 
                x="team_name", 
                y='predicted_fantasy_points', 
                color="position", 
                text='full_name', 
                color_discrete_map={ 
                    "QB": "#9CCFD6", 
                    "RB": "#DEB2AF", 
                    "WR": "#97BFF0", 
                    "TE": "#CEE1B2", 
                    "K": "#F0C397", 
                    "DEF": "#F0DB97"}, 
                category_orders={
                    "position": ["QB", "RB", "WR", "TE", "K", "DEF"]},
                hover_name="full_name",
                hover_data={
                    'predicted_fantasy_points':True,
                    'full_name':False, 'position':False, 'team_name':False
                    },
                labels={
                    "team_name":"Franchise",
                    'predicted_fantasy_points':"Predicted Points",
                }
                )
    fig.update_traces(
        textposition='inside',
    )
    fig.update_yaxes(
        visible=False
    )
    fig.add_trace(go.Scatter(
                x=total_franchise_values['team_name'], 
                y=total_franchise_values['predicted_fantasy_points'],
                text=total_franchise_values['predicted_fantasy_points'],
                mode='text',
                textposition='top center',
                textfont=dict(
                    size=12,
                ),
                showlegend=False
            ))
    fig.update_layout(
                barmode='stack', 
                xaxis={'categoryorder':'total descending'},
                plot_bgcolor='rgba(0,0,0,0)',
                title="Franchise Comparison",
                font_family="Input Serif",
                showlegend=False,
                xaxis_title=None
                )
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
    return render_template('compareFranchises.html', graphJSON=graphJSON)
  

if __name__ == "__main__":
	app.run()
