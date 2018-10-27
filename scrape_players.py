# scrape_players.py
#
# Scrapes private player data from the LearnedLeague website and saves as CSVs.
#
# Input: PLAYERS: a list of player IDs (e.g. from player_seasons.csv, but with
#                 no duplicates)
#
# Output: 1. players.csv contains each player's gender, location, college,
#            league, and referring player.
#         2. player_stats.csv contains one row per player and category with the
#            player's historical performance in that category. Note this is a
#            snapshot as of the pull date.

import pandas as pd
import mechanicalsoup


# Returns a StatefulBrowser object signed into the LearnedLeague site.
def login():
    browser = mechanicalsoup.StatefulBrowser()
    browser.open('https://www.learnedleague.com')
    browser.select_form()
    browser['username'] = 'REDACTED'
    browser['password'] = 'REDACTED'
    browser.submit_selected()
    return browser

# Given a player ID and a logged-in browser object, returns a dict of that
# player's information.
def get_player_info(player, browser):
    print(player)
    query = 'REDACTED'
    browser.open(query)
    bs = browser.get_current_page()
    try:
        text1 = bs.find_all('p', attrs={'class': 'close'})[0].text.strip()
    except IndexError:
        # perhaps because URL doesn't match ID
        return {'player': player}
    gender = text1[8:text1.index('\xa0')-1]
    location = text1[text1.index('Location')+10:]
    text2 = bs.find_all('p', attrs={'class': 'close2'})[0].text.strip()
    if text2.find('College') > -1:
        college = text2[9:]
        text3 = bs.find_all('p', attrs={'class': 'close2'})[1].text.strip()
        if text3.find('Referral') > -1:
            referral = text3[text3.index('Referral')+12:]
        else:
            referral = ''
    else:
        college = ''
        if text2.find('Referral') > -1:
            referral = text2[text2.index('Referral')+12:]
        else:
            referral = ''
    text4 = bs.find_all('p', attrs={'class': 'close'})[1].text.strip()
    text4 = text4.replace('\t', '')
    league = text4[9:text4.index('\n\n')]
    branch = text4[text4.index('Branch')+8:]
    return {'player': player, 'gender': gender, 'location': location,
            'college': college, 'league': league, 'branch': branch,
            'referral': referral}

# Given a player ID and a logged-in browser object, returns a dict of that
# player's historical stats by category.
def get_player_stats(player, browser):
    print(player)
    query = 'REDACTED'
    browser.open(query)
    bs = browser.get_current_page()
    try:
        category = [x.get_text() for x in
                      bs.find_all('td', attrs={'class': 'std-left one'})]
    except IndexError:
        # perhaps because URL doesn't match ID
        return {'player': player}
    record = [x.get_text() for x in
              bs.find_all('td', attrs={'class': 'std-mid two'})]
    pct = [x.get_text() for x in
           bs.find_all('td', attrs={'class': 'std-mid three'})]
    lgpct = [x.get_text() for x in
             bs.find_all('td', attrs={'class': 'std-mid four'})]
    correct = [x[:x.find('-')] for x in record]
    questions = [x[x.find('-')+1:] for x in record]
    return {'player': player, 'category': category, 'correct': correct,
            'questions': questions, 'pct': pct, 'lgpct': lgpct}

# Returns a DataFrame containing all info for the passed players.
def get_all_player_info(players):
    browser = login()
    data = pd.DataFrame([get_player_info(p, browser) for p in players])
    return data

# Returns a DataFrame containing historical stats for the passed players.
def get_all_player_stats(players):
    browser = login()
    data = pd.concat([pd.DataFrame.from_dict(
        get_player_stats(p, browser)) for p in players])
    return data

player_seasons = pd.read_csv('player_seasons.csv').drop_duplicates()
PLAYERS = player_seasons['player']
get_all_player_info(PLAYERS).to_csv('players.csv')
get_all_player_stats(PLAYERS).to_csv('player_stats.csv')
