# Import dependencies
import requests
import pandas as pd
from flask import Flask, redirect, request, url_for, render_template, session
from sleeperpy import User, Leagues

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
    backendapi_franchisecomparison_url = f'https://ygn5at2pt5zgycacip4t6kvrey0ayfrl.lambda-url.us-east-2.on.aws//franchise_comparison/{user_id}/{league_id}'
    response = requests.get(backendapi_franchisecomparison_url).json()
    # Parse the data
    franchise_comparisons = pd.DataFrame(response)
    # Aggregate the data
    # waiver_wire = waivers.groupby(['id_sleeper', 'team_name', 'full_name', 'age', 'team', 'number', 'position'])['predicted_fantasy_points'].sum().to_frame().reset_index()
    # waiver_wire['predicted_fantasy_points'] = waiver_wire['predicted_fantasy_points'].round(2)
    # waiver_wire = waiver_wire.drop(columns=['id_sleeper'])
    # waiver_wire = waiver_wire.sort_values('predicted_fantasy_points', ascending=False, ignore_index=True)
    franchise_comparisons = franchise_comparisons.loc[franchise_comparisons['full_name']=="Jalen Hurts"]
    return render_template("waiverWire.html", tables=[franchise_comparisons.to_html(classes='data')], titles=franchise_comparisons.columns.values)


if __name__ == "__main__":
	app.run()
