# Import dependencies
from requests_html import HTMLSession, AsyncHTMLSession

# Fetch all players from Sleeper
def fetch_all_players():
    # Use requests_html to get players since sleeper-py seems to be broken here
    session = HTMLSession()
    r = session.get('https://api.sleeper.app/v1/players/nfl')
    data = r.html.html