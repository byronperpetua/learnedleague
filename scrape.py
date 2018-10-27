# scrape.py
#
# Scrapes public data from the LearnedLeague website and saves data as CSVs.
#
# Input: SEASON    = the season number to pull data for
#        NUM_DAYS  = the length of the season in days (typically 25)
#        NUM_QS    = the number of questions per day (typically 6)
#        LEAGUES   = list of strings representing league names (may be different
#                    for each season)
#        RUNDLES   = list of strings representing rundle letters
#        DIVISIONS = list of strings representing rundle divisions, to appear at
#                    the end of each URL; '' means rundle is not divided
#
# Output: 1. responses.csv contains one row per player and question, showing
#            whether the player responded correctly, who the player's opponent
#            was, and how many defense points the opponent assigned.
#         2. player_seasons.csv contains one row per player and season, giving
#            the player's league, rundle, and division during that season.
#         3. questions.csv contains one row per question, with the category,
#            question text, and answer text.

import requests
from bs4 import BeautifulSoup
import pandas as pd
import itertools

SEASON = 77
NUM_DAYS = 25
NUM_QS = 6
LEAGUES = ['Alpine', 'Arcadia', 'Archipelago', 'Atlantic', 'Badlands', 'Bayou',
           'Canyon', 'Cascade', 'Central', 'Citadel', 'Coastal',
           'Commonwealth', 'Continental', 'Corridor', 'Delta', 'Elysium',
           'Fjord', 'Frontier', 'Garden', 'Glacier', 'Highland', 'Horizon',
           'Juniper', 'Laguna', 'Maelstrom', 'Magnolia', 'Maritime',
           'Memorial', 'Meridian', 'Metro', 'Midland', 'Morningstar', 'Nebula',
           'Olympic', 'Pacific', 'Palisade', 'Peninsula', 'Piedmont', 'Plaza',
           'Polaris', 'Prairie', 'Rubicon', 'Seaboard', 'Sequoia', 'Sierra',
           'Skyline', 'Sugarloaf', 'Summit', 'Taiga', 'Tidewater', 'Tundra',
           'Typhoon', 'Valley', 'Zephyr']
RUNDLES = ['A', 'B', 'C', 'D', 'E', 'R']
DIVISIONS = ['', '_Div_1', '_Div_2']

# Class representing the HTML source for a single LearnedLeague webpage.
class Source:
    def __init__(self, season, league, rundle, division, day, bs):
        self.season = season
        self.league = league
        self.rundle = rundle
        self.division = division
        self.day = day
        self.bs = bs

# Downloads raw source and returns  a list of Source objects for the given
# settings. One page is accessed for each season, league, rundle, division, and
# day.
def get_source(season, leagues, rundles, divisions, num_days):
    invalid = []
    source_list = []
    for combo in itertools.product(leagues, rundles, divisions,
                                   range(1, num_days+1)):
        league, rundle, division, day = combo
        if (league, rundle, division) in invalid:
            continue
        print(league, rundle, division, day)
        query = 'REDACTED'
        html = requests.get(query)
        bs = BeautifulSoup(html.content, 'html.parser')
        if bs.find('table', attrs={'summary':
                'Data table for current LL standings'}) is None:
            print('  (invalid)')
            invalid.append((league, rundle, division))
        else:
            source = Source(season, league, rundle, division, day, bs)
            source_list.append(source)
            print('  (' + str(len(source_list)) + ')')
    return source_list

# Given a list of Source objects, extracts and returns information on whether
# responses were correct and defensive points assigned.
def extract_responses(source_list, num_qs):
    responses = pd.DataFrame()
    for source in source_list:
        table = source.bs.find('table', attrs={'summary':
                'Data table for current LL standings'})
        rows = table.find_all('tr')
        players = [rows[i].find_all('td')[7].text.strip()
                for i in range(1, len(rows)-3)]
        for q in range(num_qs):
            c = [rows[i].find_all('td')[q].get('class')[0]
                    for i in range(1, len(rows)-3)]
            defense = [rows[i].find_all('td')[q].string
                        for i in range(1, len(rows)-3)]
            df = pd.DataFrame({'c': c, 'defense': defense})
            df['player'] = players
            df['season'] = source.season
            df['league'] = source.league
            df['rundle'] = source.rundle
            df['division'] = source.division
            df['day'] = source.day
            df['q_num'] = q+1
            responses = responses.append(df)
    responses.loc[responses['c'] == 'c0', 'correct'] = 0
    responses.loc[responses['c'] == 'c1', 'correct'] = 1
    del responses['c']
    responses['defense'] = pd.to_numeric(responses['defense'])
    return responses.reset_index(drop=True)

# Accepts a BeautifulSoup object representing a <div> containing question info
# and returns a dict of the question's category, text, and answer.
def get_q_info(div):
    curr = div.find('span').next_sibling
    answer = div.find_all('span')[1]
    q_text = ''
    while curr != answer:
        q_text += curr.string
        curr = curr.next_sibling
    q_text = q_text.strip()
    category = q_text[:q_text.find('-')-1]
    q_text = q_text[q_text.find('-')+2:]
    a_text = answer.string.strip()
    return {'category': category, 'q_text': q_text, 'a_text': a_text}

# Given a list of Source objects, extracts and returns the data needed for
# questions.csv.
def extract_questions(source_list, num_days):
    questions = pd.DataFrame()
    for i in range(num_days):
        source = source_list[i]
        divs = source_list[i].bs.find_all('div', attrs={'class': 'ind-Q20'})
        q_info = [get_q_info(div) for div in divs]
        df = pd.DataFrame(q_info)
        df['season'] = source.season
        df['day'] = source.day
        df['q_num'] = range(1, len(divs)+1)
        questions = questions.append(df)
    return questions.reset_index(drop=True)

# Given a list of Source objects, extracts daily matchup information.
def extract_matchups(source_list):
    matchups = pd.DataFrame()
    for source in source_list:
        table = source.bs.find('table', attrs={'class': 'tblResults'})
        rows = table.find_all('tr')
        player1 = [rows[i].find_all('td')[1].string for i in range(len(rows))]
        player2 = [rows[i].find_all('td')[3].string for i in range(len(rows))]
        df = pd.DataFrame({'player': player1, 'opponent': player2})
        df = df.append(pd.DataFrame({'player': player2, 'opponent': player1}))
        df['season'] = source.season
        df['day'] = source.day
        matchups = matchups.append(df)
    return matchups.reset_index(drop=True)

# Given a list of Source objects, extracts all information and shapes the data
# into a usable format.
def extract_all_data(source_list, num_qs, num_days):

    responses = extract_responses(source_list, num_qs)
    questions = extract_questions(source_list, num_days)
    matchups = extract_matchups(source_list)
    responses = responses.merge(matchups, on=['season', 'day', 'player'])
    player_seasons = responses[['player', 'season', 'league', 'rundle',
                               'division']].drop_duplicates()

    # Replace defense 0s with missing values if opponent forfeited
    piv = pd.pivot_table(responses, values='defense',
                         index=['season', 'day', 'opponent'],
                         aggfunc='sum').reset_index()
    piv = piv.rename(columns={'defense': 'deftotal'})
    responses = responses.merge(piv, on=['season', 'day', 'opponent'])
    responses.loc[responses['deftotal'] == 0, 'defense'] = None
    responses = responses[['defense', 'player', 'season', 'day', 'q_num',
                          'correct', 'opponent']]

    responses.to_csv('responses.csv', index=False)
    questions.to_csv('questions.csv', index=False)
    player_seasons.to_csv('player_seasons.csv', index=False)


source_list = get_source(SEASON, LEAGUES, RUNDLES, DIVISIONS, NUM_DAYS)
extract_all_data(source_list, NUM_QS, NUM_DAYS)