import os, sys, pytz
from telnetlib import STATUS
from webbrowser import get
import pandas as pd
import datetime as dt
from flask import Flask, render_template, request, redirect, url_for, session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import api_check 

app = Flask(__name__)

#DATABASE_URL = os.environ['HEROKU_POSTGRESQL_GAS_URL']
DATABASE_URL = os.environ['DATABASE_URL']
DATABASE_URL = DATABASE_URL.replace("s://", "sql://", 1)

engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
db = scoped_session(sessionmaker(bind=engine))
app.secret_key = 'pizza'

@app.route('/')
def index():
    
    CURRENT_WEEK, FIRST_UNFINISHED_WEEK = api_check.pull_current_week()

    posts = db.execute("""SELECT post_number, header, body FROM fpl_blog ORDER BY post_number DESC LIMIT 10""")
    db.commit()
    return render_template('index.html', posts=posts)

@app.route('/admin', methods= ["POST", "GET"])
def admin(): 
    status = "Running"

    return render_template("admin.html", status=status)


@app.route('/login', methods = ["POST", "GET"])
def login():

    q = "SELECT player_name FROM api_standings ORDER by player_name"
    fpl_players = db.execute(q)
    db.commit()

    df = pd.DataFrame(fpl_players.fetchall(), columns=fpl_players.keys())
    test = df['player_name'].to_list()
    

    if request.method == "POST":
        #return request.form['user_name']
        user_name = request.form["user_name"]

        q = """SELECT entry FROM api_standings WHERE UPPER(player_name) = UPPER((:user_name))"""
        user_entry = db.execute(q, {"user_name": user_name})
        db.commit()
        
        user_entry = user_entry.fetchall()
        user_entry = user_entry[0][0]   
                
        session['user_name'] = user_name
        session['user_entry'] = user_entry

        return redirect(url_for("fpl_live"))   
        
    else:
        return render_template("/login.html", fpl_players = fpl_players, test=test)

@app.route('/fpl_live')
def fpl_live():
    CURRENT_WEEK, FIRST_UNFINISHED_WEEK = api_check.pull_current_week()
    
    UPDATED_AT = dt.datetime.now(pytz.timezone('US/Central'))
    UPDATED_AT = UPDATED_AT.strftime("%Y-%m-%d at %-I:%M")

    q = f""" 
        SELECT rank_live, 
            calc_score_parts.entry, 
            CASE name
                WHEN 'NO_CHIP' THEN player_name
                ELSE CONCAT(player_name, ' (', name, ')')
                END AS player_name,
            CAST(score_3 AS int) as score_3, 
            CAST(calc_score_parts.total_points - calc_score_parts.event_transfers_cost + calc_score_parts.score_3 AS int) as Total,
            ROUND(CAST(played_games AS numeric), 1) as test, 
            price_pct_str as Salary, 
            cap.cap_player_id, 
            cap.web_name as Captain, 
            vc.vc_player_id,
            vc.web_name as Vice,
            change_str,
            CAST(expected_games AS int), 
            ROUND(CAST(salary_possible AS numeric), 1) as salary_possible,
            CAST(cap_score.score as numeric) as cap_score,
            CAST(vc_score.score as numeric) as vc_score, 
            hits.event_transfers_cost as hits,
            CAST(CASE WHEN bench_pts.pts IS NULL THEN 0 ELSE bench_pts.pts END as numeric) as bench_pts
        FROM calc_score_parts
        LEFT JOIN 
            (SELECT entry, player_name FROM api_standings) as names
            ON calc_score_parts.entry = names.entry
        LEFT JOIN 
            (SELECT entry, event, element as cap_player_id, web_name FROM api_picks LEFT JOIN (SELECT id, web_name FROM api_elements) as elements ON element = id WHERE api_picks.is_captain) as cap 
            ON calc_score_parts.entry = cap.entry
        LEFT JOIN 
            (SELECT entry, event, element as vc_player_id, web_name FROM api_picks LEFT JOIN (SELECT id, web_name FROM api_elements) as elements ON element = id WHERE api_picks.is_vice_captain) as vc
            ON calc_score_parts.entry = vc.entry
        LEFT JOIN
            (SELECT element_id, score FROM epl_live_score_gwl) AS cap_score   
            ON cap.cap_player_id = cap_score.element_id
        LEFT JOIN 
            (SELECT element_id, score FROM epl_live_score_gwl) AS vc_score
            ON vc.vc_player_id = vc_score.element_id
        LEFT JOIN 
            (SELECT entry, event_transfers_cost FROM api_history_entry WHERE event = {CURRENT_WEEK}) as hits
            on calc_score_parts.entry = hits.entry
        LEFT JOIN 
            (SELECT entry, SUM(points) as pts FROM scores_player_lvl WHERE multiplier = 0 GROUP BY entry) as bench_pts
            on calc_score_parts.entry = bench_pts.entry
        ORDER BY rank_live

    """

    live_table = db.execute(q)
    db.commit()
    
    df = pd.DataFrame(live_table.fetchall(), columns=live_table.keys())
    live_table = df.to_records(index=False)
    live_table = list(live_table)

    # #LEG 1
    # # GROUP STAGE
    CURRENT_WEEK_TEMP = 30
    groups = db.execute(f"""SELECT 
                        "Team 1 ID", "Team 1 Name", "score_1", "price_pct_str_1",
                        "Team 2 ID", "Team 2 Name", "score_2", "price_pct_str_2",
                        "Group", "Match ID"
                        FROM 
            (SELECT "Match ID", "Group", "Team 1 ID", "Team 2 ID", "Team 1 Name", "Team 2 Name" 
                FROM tbl_2122_groups WHERE "GW" = {CURRENT_WEEK_TEMP}) as GROUPS
        LEFT JOIN 
            (SELECT "entry" as entry_1, "score_3" as score_1, "price_pct_str" as "price_pct_str_1" 
            FROM "calc_score_parts") as SCOREBOARD_1
                ON GROUPS."Team 1 ID" = SCOREBOARD_1.entry_1
        LEFT JOIN 
            (SELECT "entry" as entry_2, "score_3" as score_2, "price_pct_str" as "price_pct_str_2" 
            FROM "calc_score_parts") as SCOREBOARD_2
                ON GROUPS."Team 2 ID" = SCOREBOARD_2.entry_2
        ORDER BY "Group"
        """)

    db.commit()

    #LEG 2
    # GROUP STAGE
    # CURRENT_WEEK_TEMP = 29
    # groups2 = db.execute(f"""SELECT 
    #                     "Team 1 ID", "Team 1 Name", "score_1", "price_pct_str_1",
    #                     "Team 2 ID", "Team 2 Name", "score_2", "price_pct_str_2",
    #                     "Group", "Match ID", h_leg_1.points as h_leg_1_points, a_leg_1.points as a_leg_1_points
    #                     FROM 
    #         (SELECT "Match ID", "Group", "Team 1 ID", "Team 2 ID", "Team 1 Name", "Team 2 Name" 
    #             FROM tbl_2122_groups WHERE "GW" = {CURRENT_WEEK_TEMP}) as GROUPS
    #         LEFT JOIN 
    #             (SELECT "entry" as entry_1, "score_3" as score_1, "price_pct_str" as "price_pct_str_1" 
    #             FROM "calc_score_parts") as SCOREBOARD_1
    #                 ON GROUPS."Team 1 ID" = SCOREBOARD_1.entry_1
    #         LEFT JOIN 
    #             (SELECT "entry" as entry_2, "score_3" as score_2, "price_pct_str" as "price_pct_str_2" 
    #             FROM "calc_score_parts") as SCOREBOARD_2
    #                 ON GROUPS."Team 2 ID" = SCOREBOARD_2.entry_2
    #         LEFT JOIN 
    #             (SELECT entry, points 
    #             FROM api_history_entry WHERE event = {CURRENT_WEEK_TEMP - 1}) as h_leg_1
    #             ON GROUPS."Team 1 ID" = h_leg_1.entry
    #         LEFT JOIN 
    #             (SELECT entry, points 
    #             FROM api_history_entry WHERE event = {CURRENT_WEEK_TEMP - 1}) as a_leg_1
    #             ON GROUPS."Team 2 ID" = a_leg_1.entry
    #     ORDER BY "Match ID"
    #     """)

    #d = groups2
    #db.commit()

    return render_template('fpl_live.html', live_table=live_table, groups=groups, UPDATED_AT=UPDATED_AT)   #LEG 1 
    # return render_template('fpl_live.html', live_table=live_table, groups2=groups2)         #LEG 2

@app.route('/team/<int:fpl_team_id>')
def fpl_team(fpl_team_id):

    # heading
    q = f""" 
        SELECT 
            calc_score_parts.entry, 
            CASE name
                WHEN 'NO_CHIP' THEN player_name
                ELSE CONCAT(player_name, ' (', name, ')')
                END AS player_name,        
            CAST(score_3 AS int) as score_3, 
            CAST(calc_score_parts.total_points - calc_score_parts.event_transfers_cost + calc_score_parts.score_3 AS int) as Total,
            rank_live, 
            change_str
        FROM calc_score_parts
        LEFT JOIN 
            (SELECT entry, player_name FROM api_standings) as names
            ON calc_score_parts.entry = names.entry
        WHERE calc_score_parts.entry = {fpl_team_id}
        ORDER BY rank_live        
    """

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    df['rang_gw'] = df['score_3'].rank(method='min', ascending=False).fillna(0).round().astype(int)
    dfr = df.to_records(index=False)
    heading = list(dfr)

    #body
    q = f""" SELECT * FROM 
        (SELECT 
            "element", "position", "multiplier", "is_captain", "is_vice_captain", "web_name", "team", "plural_name_short", 
            "fixture", "bps", "t_bonus", "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals", 
            "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves", "bonus", "team_a", "team_h", 
            "fix_minutes", "status_game", "status_player", "position_name", "score_3", "points", "importance"
        FROM scores_player_lvl
        WHERE entry = {fpl_team_id}) as scores_player_lvl
        LEFT JOIN (
            SELECT 
                "id", ROUND(CAST(now_cost AS numeric) / 10, 1) as cost, "points_per_game", "value_form", "value_season", "ict_index"
                "chance_of_playing_next_round", "chance_of_playing_this_round", "ep_this", "ep_next",
                "selected_by_percent", "transfers_in_event", "transfers_out_event"
            FROM api_elements
            )  as element_info
            ON scores_player_lvl.element = element_info.id
        LEFT JOIN (
            SELECT "id" as "team_id", "short_name" FROM api_teams
            ) as player_team
            ON "team" = player_team.team_id
        LEFT JOIN (
            SELECT "id" as "h_team_id", "short_name" as "home" FROM api_teams
            ) as home_team
            ON "team_h" = home_team.h_team_id
        LEFT JOIN (
            SELECT "id" as "a_team_id", "short_name" as "away" FROM api_teams
            ) as away_team
            ON "team_a" = away_team.a_team_id
        ORDER BY "position"
    """

    stats = db.execute(q)
    db.commit()

    df = pd.DataFrame(stats.fetchall(), columns=stats.keys())

    df['position_name'] = df['position_name'].fillna("None")

    print(df['position_name'].value_counts())

    fix_these = ["bps", "t_bonus", "minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals", 
            "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves", "bonus", "team_a", "team_h", 
            "fix_minutes", "score_3", "points"]
    for i in fix_these: 
        df[i] = df[i].fillna(0).astype(int)

    stats = df.to_records(index=False)
    stats = list(stats)

    return render_template('fpl_team.html', heading=heading, stats=stats)

@app.route('/player/<int:epl_player_id>/')
def epl_player(epl_player_id):
    #MAKE mapper_teams
    q = f""" SELECT id, short_name
            FROM api_teams"""
    d = db.execute(q)
    db.commit()
    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    mapper_teams = dict(zip(df.id, df.short_name))
    
    q = f""" SELECT id, first_name, second_name, team, ict_index_rank, total_points, now_cost, form
            FROM api_elements
            WHERE id = {epl_player_id}"""

    d = db.execute(q)
    db.commit()
    
    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    
    df['team'] = df['team'].map(mapper_teams)
    df['now_cost'] = df['now_cost'] / 10

    name = df['first_name'].iloc[0] + " " + df['second_name'].iloc[0]
    team = df['team'].iloc[0]
    ytd_points = df['total_points'].iloc[0]
    price_current = df['now_cost'].iloc[0]
    form = df['form'].iloc[0]

    players    = db.execute("SELECT * FROM api_element_history WHERE element = :epl_player_id", {"epl_player_id": epl_player_id})
    db.commit()

    owners     = db.execute("SELECT * FROM owners WHERE element = :player_id", {"player_id": epl_player_id})
    db.commit()
    
    return render_template("epl_player.html", name=name, team=team, ytd_points=ytd_points, price_current=price_current, form=form, players=players, owners=owners)
  
    #owned_by = current_rank, name, status

def make_roster(df, team): 
    df1_roster = df.loc[df['entry'] == team, 'element'].drop_duplicates().to_list()

    bench = []
    lineup = []
    for i in df1_roster: 
        multi = df.loc[(df['entry'] == team) & (df['element'] == i), 'multiplier'].drop_duplicates().item()
        
        if multi == 0: 
            bench.append(i)
        elif multi == 1: 
            lineup.append(i)
        elif multi > 1: 
            for j in range(multi): 
                lineup.append(i) 

    return lineup, bench

def compare_rosters(row, t1_lineup, t2_lineup, t1_bench, t2_bench):
    
    if (row['element'] in (t1_lineup)) & (row['element'] in (t2_lineup)):
        val = "both"
    elif (row['element'] in (t1_lineup)):
        if row['element'] in (t2_bench): 
            val = "team 1 only (other bench)"
        else: 
            val = "team 1 only"
    elif (row['element'] in (t2_lineup)):
        if row['element'] in (t1_bench): 
            val = "team 2 only (other bench)"
        else: 
            val = "team 2 only"
        
    else:
        val = "bench?"

    return val

def compare_captain(row):
    if (row['multiplier'] > 1):
        val = row['web_name'] + "(" + str(row['multiplier']) + "x)"
    else:
        val = row['web_name']

    return val

def compare_rollup_player(row):
    if (row['status_game'] == "Game Over"):
        val = "Match Over"
    else:
        val = row['web_name_adj']

    return val

def compare_rollup_match(row):
    if (row['status_game'] == "Game Over"):
        val = "-"
    else:
        val = row['match']

    return val

def get_score(team):
    q = f""" SELECT CAST(score_3 AS int) as score_3 FROM calc_score_parts WHERE entry = {team}"""

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    
    return df.score_3.item()

@app.route('/compare/<int:team1>/<int:team2>')
def compare(team1, team2): 
    
    q_base = f""" SELECT "element", "web_name", "plural_name_short", "player_name", "multiplier", 
                CONCAT("status_game", ' | ', "status_player") as status, CAST("score_3" as INT), 
                CONCAT("home", ' | ', "away") as match, CAST("points" as INT), "entry", "status_game" 
            FROM (
                SELECT "element", "web_name", "plural_name_short", "player_name", "multiplier", 
                    "status_game", "status_player", "score_3", "points", "team_h", "team_a", "entry" FROM scores_player_lvl) as main
            LEFT JOIN (
                SELECT "id" as "h_team_id", "short_name" as "home" FROM api_teams) as home_team
                ON "team_h" = home_team.h_team_id
            LEFT JOIN (
                SELECT "id" as "a_team_id", "short_name" as "away" FROM api_teams) as away_team
                ON "team_a" = away_team.a_team_id
    """

    ###############################################################
    ###############################################################
    # CAPTAIN
    #TEAM 1 
    q_var = f"""WHERE entry = {team1} AND multiplier > 1
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t1_cap = db.execute(q)
    db.commit()

    #TEAM 2 
    q_var = f"""WHERE entry = {team2} AND multiplier > 1
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t2_cap = db.execute(q)
    db.commit()

    ###############################################################
    ###############################################################
    # GKP 
    #TEAM 1 
    q_var = f"""WHERE entry = {team1} AND plural_name_short = 'GKP' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t1_gkp = db.execute(q)
    db.commit()

    #TEAM 2 
    q_var = f"""WHERE entry = {team2} AND plural_name_short = 'GKP' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t2_gkp = db.execute(q)
    db.commit()

    ###############################################################
    ###############################################################
    # DEF 
    #TEAM 1 
    q_var = f"""WHERE entry = {team1} AND plural_name_short = 'DEF' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t1_def = db.execute(q)
    db.commit()

    #TEAM 2 
    q_var = f"""WHERE entry = {team2} AND plural_name_short = 'DEF' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t2_def = db.execute(q)
    db.commit()

    ###############################################################
    ###############################################################
    # MID 
    #TEAM 1 
    q_var = f"""WHERE entry = {team1} AND plural_name_short = 'MID' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t1_mid = db.execute(q)
    db.commit()

    #TEAM 2 
    q_var = f"""WHERE entry = {team2} AND plural_name_short = 'MID' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t2_mid = db.execute(q)
    db.commit()

    ###############################################################
    ###############################################################
    # FWD 
    #TEAM 1 
    q_var = f"""WHERE entry = {team1} AND plural_name_short = 'FWD' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t1_fwd = db.execute(q)
    db.commit()

    #TEAM 2 
    q_var = f"""WHERE entry = {team2} AND plural_name_short = 'FWD' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t2_fwd = db.execute(q)
    db.commit()

    q = f"""SELECT entry, player_name FROM api_standings WHERE entry = {team1}"""
    t1_name = db.execute(q)
    db.commit()

    df = pd.DataFrame(t1_name.fetchall(), columns=t1_name.keys())
    t1_name = df.to_records(index=False)
    t1_name = list(t1_name)

    q = f"""SELECT entry, player_name FROM api_standings WHERE entry = {team2}"""
    t2_name = db.execute(q)
    db.commit()

    df = pd.DataFrame(t2_name.fetchall(), columns=t2_name.keys())
    t2_name = df.to_records(index=False)
    t2_name = list(t2_name)

    #TEAM 2 
    q_var = f"""WHERE entry = {team2} AND plural_name_short = 'FWD' AND multiplier < 2
                ORDER BY score_3 DESC"""

    q = q_base + q_var

    t2_fwd = db.execute(q)
    db.commit()

    #ROSTERS 
    q_var = f"""WHERE entry = {team1} or entry = {team2}"""

    q = q_base + q_var
    
    d= db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    df.loc[df['match'] == 'BUR | WAT', 'status_game'] = "Pending"    

    t1_lineup, t1_bench = make_roster(df, team1)
    t2_lineup, t2_bench = make_roster(df, team2)

    df['compare'] = df.apply(compare_rosters, args=(t1_lineup, t2_lineup, t1_bench, t2_bench), axis=1)
    df['web_name_adj'] = df.apply(compare_captain, axis=1)
    df['rollup_player'] = df.apply(compare_rollup_player, axis=1)
    df['rollup_match'] = df.apply(compare_rollup_match, axis=1)

    m = {team1 : "team1", team2: "team2"}
    df['player_name_2'] = df['entry'].map(m)

    dft = df.loc[(df['compare'] == "both"), :]
    both = pd.pivot_table(dft, index='rollup_player', columns='player_name_2', values='score_3', aggfunc='sum').reset_index()
    
    try: 
        both['team1'] = both['team1'].astype(int)
        both = both.sort_values("team1", ascending=False)
        both['team2'] = both['team2'].astype(int)
        both = both.sort_values("team2", ascending=False)
    except: 
        pass
    both = both.to_records(index=False)
    both = list(both)

    #dft = df.loc[(df['compare'].isin(['team 1 only (other bench)', 'team 1 only'])), :]
    dft = df.loc[(df['compare'].isin(['team 1 only (other bench)', 'team 1 only'])), :]
    diff_1 = pd.pivot_table(dft, index=['rollup_player', 'rollup_match'], columns='player_name_2', values='score_3', aggfunc='sum').reset_index()
    diff_1 = diff_1.sort_values('team1',ascending=False)
    diff_1['team1'] = diff_1['team1'].astype(int)
    diff_1 = diff_1.to_records(index=False)
    diff_1 = list(diff_1)

    dft = df.loc[(df['compare'].isin(['team 2 only (other bench)', 'team 2 only'])), :]
    #dft = df.loc[(df['compare'].isin(['team 2 only'])), :]
    diff_2 = pd.pivot_table(dft, index=['rollup_player', 'rollup_match'], columns='player_name_2', values='score_3', aggfunc='sum').reset_index()
    diff_2 = diff_2.sort_values('team2',ascending=False)
    diff_2['team2'] = diff_2['team2'].astype(int)
    try: 
        diff_2 = diff_2.drop(columns=['team1'])
    except: 
        pass
    diff_2 = diff_2.to_records(index=False)
    
    diff_2 = list(diff_2)

    score_1 = get_score(team1)
    score_2 = get_score(team2)

    return render_template('compare.html', t1_cap=t1_cap, t2_cap=t2_cap, t1_gkp=t1_gkp, t2_gkp=t2_gkp, 
                                            t1_def=t1_def, t2_def=t2_def, t1_mid=t1_mid, t2_mid=t2_mid, 
                                            t1_fwd=t1_fwd, t2_fwd=t2_fwd, t1_name=t1_name, t2_name=t2_name, 
                                            both=both, diff_1=diff_1, diff_2=diff_2, t2_bench=t2_bench, 
                                            score_1=score_1, score_2=score_2)

@app.route('/run_search', methods= ['POST'])
def run_search():
    if request.method == 'POST':
        search_for = request.form['search_for']
        search_for_like = "%" + search_for + "%"
        #elements = db.execute("SELECT * FROM api_elements WHERE UPPER(api_elements.\"web_name\") LIKE UPPER(:search_for_like) OR UPPER(\"api_elements\".\"second_name\") LIKE UPPER(:search_for_like)", {"search_for_like":search_for_like})
        #elements = db.execute(""" SELECT * FROM api_elements WHERE UPPER(api_elements.web_name) LIKE UPPER(:search_for_like) """ , {"search_for_like":search_for_like})
        elements = db.execute(f""" 
        SELECT * FROM "api_elements" WHERE UPPER("web_name") LIKE UPPER('%{search_for}%')
        """) 

    #body
    q = f""" SELECT s_elements.element,s_elements.first_name,s_elements.second_name,s_elements.web_name,s_elements.team,
            s_elements.element_type,s_stats.index,s_stats.element_id,s_stats.fixture,s_stats.minutes as mins_player,s_stats.goals_scored,
            s_stats.assists,s_stats.clean_sheets,s_stats.goals_conceded,s_stats.own_goals,s_stats.penalties_saved,s_stats.penalties_missed,
            s_stats.yellow_cards,s_stats.red_cards,s_stats.saves,s_stats.bonus,s_bps.bps,s_bps.t_bonus,player_team.team_id,
            player_team.short_name,s_epl_scores.kickoff_time,s_epl_scores.finished,s_epl_scores.finished_provisional,
            s_epl_scores.minutes as mins_team,s_epl_scores.started,s_epl_scores.team_a,s_epl_scores.team_h,home_team.h_team_id,
            home_team.home,away_team.a_team_id,away_team.away,s_fix_mins.fix_minutes, s_stats_f1.points

        FROM 
            (SELECT id as "element", first_name, second_name, web_name, team, element_type FROM api_elements) as s_elements 
            LEFT JOIN (
                SELECT * FROM "api_fpl_stats_f2") as s_stats
                ON s_elements.element = s_stats.element_id 
            LEFT JOIN ( 
                SELECT element_id, fixture, points FROM api_fpl_stats_f1) as s_stats_f1 
                ON s_stats.element_id = s_stats_f1.element_id AND s_stats.fixture = s_stats_f1.fixture
            LEFT JOIN (
                SELECT element_id, fixture, bps, t_bonus FROM api_bps_f) as s_bps ON 
                s_stats.element_id = s_bps.element_id AND s_stats.fixture = s_bps.fixture
            LEFT JOIN (
                SELECT "id" as "team_id", "short_name" FROM api_teams) as player_team
                ON s_elements."team" = player_team.team_id  
            LEFT JOIN ( 
                SELECT id as fixture, kickoff_time, finished, finished_provisional, minutes, started, team_a, team_h FROM api_epl_scores) as s_epl_scores 
                ON s_stats.fixture = s_epl_scores.fixture 
            LEFT JOIN (
                SELECT "id" as "h_team_id", "short_name" as "home" FROM api_teams) as home_team
                ON "team_h" = home_team.h_team_id
            LEFT JOIN (
                SELECT "id" as "a_team_id", "short_name" as "away" FROM api_teams) as away_team
                ON "team_a" = away_team.a_team_id
            LEFT JOIN (
                SELECT fixture, MAX(api_fpl_stats.value) as fix_minutes FROM api_fpl_stats WHERE identifier = 'minutes' GROUP BY fixture) as s_fix_mins 
                ON s_stats.fixture = s_fix_mins.fixture
            WHERE UPPER("web_name") LIKE UPPER('%{search_for}%') OR UPPER(player_team.short_name) LIKE UPPER('%{search_for}%') 
        ORDER BY points DESC
            """

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    df = df.fillna(0)

    fix_these = ["bps", "t_bonus", "fix_minutes", "goals_scored", "assists", "clean_sheets", "goals_conceded", "own_goals", 
            "penalties_saved", "penalties_missed", "yellow_cards", "red_cards", "saves", "bonus", "team_a", "team_h", 
            "fix_minutes", "points"]
    for i in fix_these: 
        df[i] = df[i].fillna(0).astype(int)

    stats = df.to_records(index=False)
    stats = list(stats)
    
    db.commit()
    return render_template('fpl_search_results.html', stats=stats, search_for=search_for)

@app.route('/fpl_cup')
def fpl_cup():
    # cup table - GROUP A
    q = f""" SELECT "Group", "Team", "Name", CAST("Points" as INT), CAST("W" as INT), CAST("D" as INT), CAST("L" as INT) 
    FROM cup_static_table
    WHERE "Group" = 'A' """

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    dfr = df.to_records(index=False)
    cup_table_a = list(dfr)

    # cup table - GROUP B
    q = f""" SELECT "Group", "Team", "Name", CAST("Points" as INT), CAST("W" as INT), CAST("D" as INT), CAST("L" as INT) 
    FROM cup_static_table
    WHERE "Group" = 'B' """

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    dfr = df.to_records(index=False)
    cup_table_b = list(dfr)

    # cup table - GROUP C
    q = f""" SELECT "Group", "Team", "Name", CAST("Points" as INT), CAST("W" as INT), CAST("D" as INT), CAST("L" as INT) 
    FROM cup_static_table
    WHERE "Group" = 'C' """

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    dfr = df.to_records(index=False)
    cup_table_c = list(dfr)

    # cup table - GROUP D
    q = f""" SELECT "Group", "Team", "Name", CAST("Points" as INT), CAST("W" as INT), CAST("D" as INT), CAST("L" as INT) 
    FROM cup_static_table
    WHERE "Group" = 'D' """

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    dfr = df.to_records(index=False)
    cup_table_d = list(dfr)

    # cup table - GROUP E
    q = f""" SELECT "Group", "Team", "Name", CAST("Points" as INT), CAST("W" as INT), CAST("D" as INT), CAST("L" as INT) 
    FROM cup_static_table
    WHERE "Group" = 'E' """

    d = db.execute(q)
    db.commit()

    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    dfr = df.to_records(index=False)
    cup_table_e = list(dfr)

    return render_template('fpl_cup.html', cup_table_a=cup_table_a, 
        cup_table_b=cup_table_b, 
        cup_table_c=cup_table_c, 
        cup_table_d=cup_table_d, 
        cup_table_e=cup_table_e)


##################################################################
#PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS 
#PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS 
@app.route('/picks')
def picks():
    if "user" in session:
        #return render_template('picks.html')
        return redirect(url_for('picks_home'))
    else:
        return redirect(url_for("picks_login"))

@app.route('/picks/register', methods = ["POST", "GET"])
def picks_register():
    if request.method == 'POST':
        session['name'] = request.form["name"]
        #session['user'] = request.form["email"]
        session['password_choice'] = request.form["password_choice"]
        session['userid'] = request.form["userid"]       
        session['user_id'] = request.form["userid"]       

        db.execute(
            """INSERT INTO fpl_picks_users ("user_id", "name", "password") VALUES (:x, :y, :z)""", 
            {"x": session['userid'], "y": session['name'], "z": session['password_choice']})
        #db.execute("UPDATE name_list_g SET \"Michelle\" = (:x) WHERE \"Name\" = (:y)", {"x": x, "y":y})
        db.commit()

        return redirect(url_for('picks_home'))

    if request.method == 'GET':
        if "user" in session:
            pass # logout and send to register 
        else:
            #get password 
            r_word_list = db.execute("""SELECT words_med FROM z_wordlist_med """)
            db.commit()

            word_list = r_word_list.fetchall()
            LIST_LEN = len(word_list)

            passwords = [] 
            for i in range(5): 
                x = word_list[random.choice(range(LIST_LEN))][0]
                y = word_list[random.choice(range(LIST_LEN))][0]
                password = x + "_" + y
                passwords.append(password)

            #get new user key
            r_userid = db.execute("""SELECT max(user_id) FROM fpl_picks_users """)
            db.commit()

            userid = r_userid.fetchall()

            userid = userid[0][0] + 1 

            #send to register
            return render_template('/picks/p_register.html', passwords=passwords, userid=userid)

@app.route('/picks/login', methods = ["POST", "GET"])
def picks_login():

    if request.method == "POST":
        subbed_name = request.form["name"]
        subbed_password = request.form["password"]

        q = """SELECT user_id, password FROM fpl_picks_users WHERE UPPER(name) = UPPER((:subbed_name))"""
        user_check = db.execute(q, {"subbed_name": subbed_name})
        db.commit()

        if user_check.rowcount == 0: 
            #TODO
            print("error")
        else: 
            user_check = user_check.fetchall()

            user_id = user_check[0][0]            
            password_answer = user_check[0][1]
            
        if password_answer == subbed_password:
            session['user_id'] = user_id
            session['name'] = subbed_name

            return redirect(url_for("picks_home"))   

        else: 
            return redirect(url_for("picks_login"))    
        
    else:
        return render_template("/picks/p_login.html")

@app.route('/picks/home')
def picks_home(): 
    return render_template('/picks/p_home.html')

@app.route('/picks/scores/event=<int:event>')
def picks_scores_event(event):
    test = request.args.get('username')
    q = """
            SELECT d.event, d.code, a.ts, d.london, c.name, e.short_name as away, f.short_name as home, CAST("team_a_score" AS INTEGER), CAST("team_h_score" AS INTEGER),
            CASE
                WHEN team_a_score = team_h_score THEN 'pick_t'
                WHEN team_a_score > team_h_score THEN 'pick_a'
                ELSE 'pick_h'
                END AS game_result,
            b.pick as points, b.choice,
            CASE
                WHEN choice = (CASE
                WHEN team_a_score = team_h_score THEN 'pick_t'
                WHEN team_a_score > team_h_score THEN 'pick_a'
                ELSE 'pick_h'
                END) THEN b.pick
                ELSE b.pick * -1 
                END AS effective_points, 
            d.london < (select now()) as game_started
            FROM 
            (SELECT "code", "user_id", MAX("timestamp") as ts
            FROM "fpl_picks_picks"
            GROUP BY "user_id", "code"
            ) as a
            LEFT JOIN
            (SELECT "code", "user_id", "timestamp", "pick", "choice"
            FROM "fpl_picks_picks"
            ) as b
            ON a.code = b.code AND a.user_id = b.user_id and a.ts = b.timestamp
            LEFT JOIN 
            (SELECT "user_id", "name", "active"
            FROM "fpl_picks_users"
            ) as c
            ON a.user_id = c.user_id
            LEFT JOIN
            (SELECT "code", "team_a", "team_h", "london", "team_a_score", "team_h_score", "event"
            FROM "fpl_picks_schedule"
            ) as d
            ON a.code = d.code
            LEFT JOIN
            (SELECT "id", "short_name"
            FROM "fpl_picks_teams"
            ) as e
            on d.team_a = e.id
            LEFT JOIN
            (SELECT "id", "short_name"
            FROM "fpl_picks_teams"
            ) as f
            on d.team_h = f.id
            WHERE "active" = 1 AND  d.london < (select now()) AND event = :event
            ORDER BY d.london, d.code, name
        """

    scores = db.execute(q, {'event':int(event)})
    db.commit()

    d = db.execute(q, {'event':int(event)})
    db.commit()
    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    df['match_name'] = df['home'] + "_" + df['away']
    dfp = pd.pivot_table(df, index='name', columns='match_name', values='effective_points', aggfunc=sum, margins=True).reset_index().sort_values('All', ascending=False)
    #dfp["name2"] = '<a href="/' + dfp["name"] + '">' + dfp["name"] + "</a>"

    return render_template('picks/p_scores.html', 
        scores=scores, 
        test=test, 
        tables=[
            dfp.to_html(index=False, 
                index_names=False, 
                justify='center', 
                bold_rows='False', 
                classes=['table table-sm text-xsmall table-hover sortable align-middle'], 
                render_links=True, 
                escape=False)], 
        titles=event)

@app.route('/picks/scores')
def picks_scores():
    event = request.args.get('event')

    if event == None: 
        event = FIRST_UNFINISHED_WEEK

    return redirect(f'/picks/scores/event={event}')
    
@app.route('/picks/scores/summary')
def picks_scores_summary():
    
    q = """
    SELECT aa.name as Name, SUM(points) as Wagered, SUM(test3) as Score FROM  
    (SELECT a.code, a.user_id, a.ts, c.name, d.team_a, d.team_h, e.name as away, f.name as home, 
    b.pick as points, b.choice, d.london, "team_a_score", "team_h_score", d.london < (select now()) as test,
        CASE
            WHEN team_a_score = team_h_score THEN 'pick_t'
            WHEN team_a_score > team_h_score THEN 'pick_a'
            ELSE 'pick_h'
        END AS test2,
        CASE
            WHEN choice = (CASE
            WHEN team_a_score = team_h_score THEN 'pick_t'
            WHEN team_a_score > team_h_score THEN 'pick_a'
            ELSE 'pick_h'
        END) THEN b.pick
            ELSE b.pick * -1 
        END AS test3
    FROM 
    (SELECT "code", "user_id", MAX("timestamp") as ts
    FROM "fpl_picks_picks"
    GROUP BY "user_id", "code"
    ) as a
    LEFT JOIN
    (SELECT "code", "user_id", "timestamp", "pick", "choice"
    FROM "fpl_picks_picks"
    ) as b
    ON a.code = b.code AND a.user_id = b.user_id and a.ts = b.timestamp
    LEFT JOIN 
    (SELECT "user_id", "name", "active"
    FROM "fpl_picks_users"
    ) as c
    ON a.user_id = c.user_id
    LEFT JOIN
    (SELECT "code", "team_a", "team_h", "london", "team_a_score", "team_h_score", event
    FROM "fpl_picks_schedule"
    ) as d
    ON a.code = d.code
    LEFT JOIN
    (SELECT "id", "name"
    FROM "fpl_picks_teams"
    ) as e
    on d.team_a = e.id
    LEFT JOIN
    (SELECT "id", "name"
    FROM "fpl_picks_teams"
    ) as f
    on d.team_h = f.id
    """ 

    sq1 = """
    WHERE "active" = 1 AND  d.london < (select now())) as aa 
    GROUP BY aa.user_id, aa.name
    ORDER BY Score DESC
    """

    sq2 = """
    WHERE "active" = 1 AND  d.london < (select now()) AND d.event = :gameweek) as aa 
    GROUP BY aa.user_id, aa.name
    ORDER BY Score DESC
    """

    scores_summ_sesn = db.execute(q + sq1)
    scores_summ_week  = db.execute(q + sq2, {"gameweek" : CURRENT_WEEK})
    db.commit()

    season_long_pts = """SELECT "Name", "Current Pts" FROM fpl_picks_sesonlong ORDER BY "Current Pts" DESC """
    sl_points = db.execute(season_long_pts)
    db.commit()

    indy  = """SELECT "Name", "Golden Boot", "Most Assists", "Golden Glove", "Sack Race 1" FROM fpl_picks_sesonlong"""
    indys = db.execute(indy)
    db.commit()

    top4  = """SELECT "Name", "Champ", "Top 4 (2)", "Top 4 (3)", "Top 4 (4)" FROM fpl_picks_sesonlong """
    top4s = db.execute(top4)
    db.commit()

    europa  = """SELECT "Name", "Eurpoa (1)", "Eurpoa (2)", "Eurpoa (3)" FROM fpl_picks_sesonlong """
    europas = db.execute(europa) 
    db.commit()

    mid  = """SELECT "Name", "Mid Table (1)", "Mid Table (2)", "Mid Table (3)", "Mid Table (4)", "Mid Table (5)" FROM fpl_picks_sesonlong """
    mids = db.execute(mid) 
    db.commit()

    bot  = """SELECT "Name", "Bottom Half (1)", "Bottom Half (2)", "Bottom Half (3)", "Bottom Half (4)", "Bottom Half (5)" FROM fpl_picks_sesonlong """
    bots = db.execute(bot) 
    db.commit()

    relg  = """SELECT "Name", "Relegation (1)", "Relegation (2)", "Relegation (3)" FROM fpl_picks_sesonlong """
    relgs = db.execute(relg) 

    db.commit()

    return render_template('/picks/p_scores_summary.html', scores_summ_sesn = scores_summ_sesn, scores_summ_week=scores_summ_week, 
        sl_points=sl_points, indys=indys, top4s=top4s, europas=europas, mids=mids, bots=bots, relgs=relgs)

@app.route('/picks/make_picks')
def make_picks_router(): 
    
    CURRENT_WEEK, FIRST_UNFINISHED_WEEK = api_check.pull_current_week()

    return redirect(f'/picks/make_picks/{FIRST_UNFINISHED_WEEK}')
    #return redirect(url_for(make_picks_router))

@app.route('/picks/make_picks/<int:gameweek>')
def make_picks(gameweek): 
    
    #print("browser time: ", request.args.get("time"))

    #print("server time : ", time.strftime('%A %B, %d %Y %H:%M:%S'));
    asdf = dt.datetime.now()

    # q = """SELECT "code", "kickoff_time", h_team."team_h", a_team."team_a" FROM
    # ((SELECT "code", "kickoff_time", "minutes", "team_a", "team_h" FROM fpl_picks_schedule WHERE event = :gameweek) as sch
    # LEFT JOIN 
    # (SELECT "id", "short_name" as "team_h", "points" as "points_h" FROM "fpl_picks_teams") as h_team
    # ON sch.team_h = h_team.id
    # LEFT JOIN 
    # (SELECT "id", "short_name" as "team_a", "points" as "points_a" FROM "fpl_picks_teams") as a_team
    # ON sch.team_a = a_team.id)"""

    q = """ 
        SELECT sch."code", "london_str", h_team."team_h", a_team."team_a", picks."choice", picks."pick", "london" FROM
        ((SELECT "code", "london_str", "minutes", "team_a", "team_h", "london" FROM fpl_picks_schedule WHERE event = :gameweek) as sch
        LEFT JOIN 
        (SELECT "id", "name" as "team_h", "points" as "points_h" FROM "fpl_picks_teams") as h_team
        ON sch.team_h = h_team.id
        LEFT JOIN 
        (SELECT "id", "name" as "team_a", "points" as "points_a" FROM "fpl_picks_teams") as a_team
        ON sch.team_a = a_team.id
        LEFT JOIN 
        (SELECT "p_code" as "code", "u_pick" as "pick", "u_choice" as "choice", "p_user_id" as "user_id" FROM 
        ((SELECT "code" as "p_code", "user_id" as "p_user_id", MAX(timestamp) as p_ts FROM "fpl_picks_picks" WHERE "user_id" = :user_id
        GROUP BY "code", "user_id"
        ) AS tbl_p
        LEFT JOIN
        (SELECT "code" as "u_code",
        "user_id" as "u_user_id",
        "timestamp" as "u_timestamp",
        "pick" as "u_pick",
        "choice" as "u_choice" FROM "fpl_picks_picks" 
        ) AS tbl_u
        ON tbl_p.p_code = tbl_u.u_code AND tbl_p.p_user_id = tbl_u.u_user_id AND tbl_p.p_ts = tbl_u.u_timestamp) as a
        WHERE "p_user_id" = :user_id) as picks
        ON sch.code = picks.code)
        ORDER BY  "london_str", sch.code
    """ #(SELECT "code", "pick", "choice", "user_id" FROM "fpl_picks_picks" WHERE "user_id" = :user_id)

    #q = """SELECT * FROM fpl_picks_schedule WHERE event = :gameweek"""
    week_schedule = db.execute(q, {"gameweek" : gameweek, "user_id": session["user_id"]})
    db.commit()

    return render_template('picks/p_make_picks.html', current_week=CURRENT_WEEK, week_schedule=week_schedule, asdf=asdf)

@app.route('/picks/make_picks/match/<int:match_number>', methods=['POST', 'GET'])
def make_picks_match(match_number): 
    if request.method == 'GET':
        #check user in session 
        q = """SELECT "london_str", h_team."team_h", a_team."team_a" FROM
        ((SELECT "code", "london_str", "minutes", "team_a", "team_h" FROM fpl_picks_schedule WHERE code = :match_number) as sch
        LEFT JOIN 
        (SELECT "id", "name" as "team_h", "points" as "points_h" FROM "fpl_picks_teams") as h_team
        ON sch.team_h = h_team.id
        LEFT JOIN 
        (SELECT "id", "name" as "team_a", "points" as "points_a" FROM "fpl_picks_teams") as a_team
        ON sch.team_a = a_team.id)"""

 
        single_game = db.execute(q, {"match_number" : match_number})
        db.commit()

        single_game = single_game.fetchall()

        match_number = match_number
        #date_time = dt.strptime(single_game[0][0], '%d/%m/%y %H:%M:%S')
        #date_time = date_time.dt.tz_convert('US/Central')
        #date_time = dt.fromisoformat(single_game[0][0])

        #date_time = parser.isoparse(single_game[0][0])
        #date_time = date_time.strftime("%a %m-%d at %H:%M")

        date_time = single_game[0][0]
        team_h = single_game[0][1]
        team_a = single_game[0][2]
        
        return render_template('picks/p_match.html', match_number=match_number, date_time=date_time, team_h=team_h, team_a=team_a)

    else: 
        
        choice = request.form["choice"]
        wager = request.form["wager"]
        ts_now = dt.datetime.now()

        db.execute(
            """INSERT INTO fpl_picks_picks ("user_id", "code", "pick", "timestamp", "choice") VALUES (:v, :w, :x, :y, :z)""", 
            {"v": session["user_id"], "w": match_number, "x": wager, "y": ts_now, "z": choice})

        db.commit()

        return redirect("/picks/make_picks")

@app.route('/picks/checker')
def picks_checker():

    q = """ 
        SELECT c.name, COUNT(b.choice), d.event
        FROM 
        (SELECT "code", "user_id", MAX("timestamp") as ts
        FROM "fpl_picks_picks"
        GROUP BY "user_id", "code"
        ) as a
        LEFT JOIN
        (SELECT "code", "user_id", "timestamp", "pick", "choice"
        FROM "fpl_picks_picks"
        ) as b
        ON a.code = b.code AND a.user_id = b.user_id and a.ts = b.timestamp
        LEFT JOIN 
        (SELECT "user_id", "name", "active"
        FROM "fpl_picks_users"
        ) as c
        ON a.user_id = c.user_id
        LEFT JOIN
        (SELECT "code", "team_a", "team_h", "london", "team_a_score", "team_h_score", "event"
        FROM "fpl_picks_schedule"
        ) as d
        ON a.code = d.code
        LEFT JOIN
        (SELECT "id", "name"
        FROM "fpl_picks_teams"
        ) as e
        on d.team_a = e.id
        LEFT JOIN
        (SELECT "id", "name"
        FROM "fpl_picks_teams"
        ) as f
        on d.team_h = f.id
        WHERE "event" = :FIRST_UNFINISHED_WEEK
        GROUP BY c.name, d.event
    """ #WHERE "event" = :CURRENT_WEEK OR "event" = :FIRST_UNFINISHED_WEEK

    summary = db.execute(q, {"CURRENT_WEEK" : CURRENT_WEEK, "FIRST_UNFINISHED_WEEK":FIRST_UNFINISHED_WEEK})
    db.commit()

    q = """
        SELECT d.code, d.london, c.name, e.name, f.name, COUNT(b.choice)
        FROM 
        (SELECT "code", "user_id", MAX("timestamp") as ts
        FROM "fpl_picks_picks"
        GROUP BY "user_id", "code"
        ) as a
        LEFT JOIN
        (SELECT "code", "user_id", "timestamp", "pick", "choice"
        FROM "fpl_picks_picks"
        ) as b
        ON a.code = b.code AND a.user_id = b.user_id and a.ts = b.timestamp
        LEFT JOIN 
        (SELECT "user_id", "name", "active"
        FROM "fpl_picks_users"
        ) as c
        ON a.user_id = c.user_id
        LEFT JOIN
        (SELECT "code", "team_a", "team_h", "london", "team_a_score", "team_h_score", "event"
        FROM "fpl_picks_schedule"
        ) as d
        ON a.code = d.code
        LEFT JOIN
        (SELECT "id", "name"
        FROM "fpl_picks_teams"
        ) as e
        on d.team_a = e.id
        LEFT JOIN
        (SELECT "id", "name"
        FROM "fpl_picks_teams"
        ) as f
        on d.team_h = f.id
        WHERE "event" = :FIRST_UNFINISHED_WEEK
        GROUP BY d.code, d.london, c.name, e.name, f.name
        ORDER BY d.london, d.code
    """ #WHERE "event" = :CURRENT_WEEK

    details = db.execute(q, {"CURRENT_WEEK" : CURRENT_WEEK, "FIRST_UNFINISHED_WEEK" : FIRST_UNFINISHED_WEEK})
    db.commit()

    return render_template('picks/p_checker.html', summary=summary, details=details)

@app.route("/picks/logout", methods = ["POST", "GET"])
def picks_logout():
    try: 
        session.pop('name')
    except:
        pass

    try:
        session.pop('password_choice')
    except:
        pass    

    try:
        session.pop('userid')
    except:
        pass        

    try: 
        session.pop('user_id')
    except:
        pass

    try: 
        session.pop('user')
    except:
        pass

    db.remove()

    return redirect(url_for("picks_login"))

#PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS 
#PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS PICKS 
##################################################################

#FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB 
#FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB 
@app.route("/fbb")
def fbb(): 
    if "fbb_user" in session:
        return render_template('/fbb/z3_fbb.html')
    else:
        return redirect(url_for("fbb_login"))

@app.route("/fbb/login", methods = ["POST", "GET"])
def fbb_login():
    if request.method == "POST":
        fbb_user = request.form["fbb_user"]
        session['fbb_user'] = fbb_user

        #fbb_team_name = db.execute(""" SELECT * FROM "fbb_teams" WHERE short_name = :fbb_user""", {"fbb_user" : fbb_user}) 
        #session['fbb_team_name'] = fbb_team_name
        return redirect(url_for("fbb_leaderboard", fbb_user=fbb_user)) #, fbb_team_name = fbb_team_name
    else:
        return render_template("fbb/z3_login.html")

@app.route("/fbb/team/<int:team_id>")
def fbb_team(team_id):
    
    time = db.execute("SELECT DISTINCT * FROM fbb_espn WHERE index = 0")

    #hitters  = db.execute("""SELECT * FROM fbb_espn WHERE team_id = :team_id AND "fbb_espn.scoringPeriodId" = 7""", {"team_id": team_id})
    hitters = db.execute("""SELECT * FROM fbb_espn 
    WHERE team_id = :team_id AND 
    "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
    "fbb_espn"."lineupSlotId" NOT IN (13, 16, 17)
    ORDER BY "fbb_espn"."lineupSlotId"
    """, {"team_id": team_id})

    pitchers = db.execute("""SELECT * FROM fbb_espn 
    WHERE team_id = :team_id AND 
    "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
    "fbb_espn"."lineupSlotId" IN (13)
    ORDER BY "fbb_espn"."lineupSlotId"
    """, {"team_id": team_id})

    bench = db.execute("""SELECT * FROM fbb_espn 
    WHERE team_id = :team_id AND 
    "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
    "fbb_espn"."lineupSlotId" IN (16, 17)
    ORDER BY "fbb_espn"."lineupSlotId"
    """, {"team_id": team_id})

    owner1 = db.execute("""
    SELECT * FROM "fbb_teams" WHERE team_id = :team_id  
    """, {"team_id": team_id})

    owner2 = db.execute("""
    SELECT * FROM "fbb_teams" WHERE team_id = :team_id  
    """, {"team_id": team_id})

    #owner = db.execute(owner, {"team_id": team_id})
    #owner_f = format_results(owner)

    #owner_name = owner_f[0]['owner']
    db.commit()

    return render_template("fbb/z3_team.html", hitters=hitters, pitchers=pitchers, bench=bench, owner1=owner1, owner2=owner2, time=time) #, owner_name=owner_name)

@app.route("/fbb/team/<int:team_id>/<int:gameday>")
def fbb_team_specific(team_id, gameday):
    time = db.execute("SELECT DISTINCT * FROM fbb_espn WHERE index = 0")

    hitters = db.execute("""SELECT * FROM fbb_espn_attic 
    WHERE 
    team_id = :team_id AND 
    "fbb_espn_attic"."scoringPeriodId" = :gameday AND 
    "fbb_espn_attic"."lineupSlotId" NOT IN (13, 16, 17)
    ORDER BY "fbb_espn_attic"."lineupSlotId"
    """, {"team_id": team_id, "gameday": gameday})

    pitchers = db.execute("""SELECT * FROM fbb_espn_attic 
    WHERE 
    team_id = :team_id AND 
    "fbb_espn_attic"."scoringPeriodId" = :gameday AND 
    "fbb_espn_attic"."lineupSlotId" IN (13)
    ORDER BY "fbb_espn_attic"."lineupSlotId"
    """, {"team_id": team_id, "gameday": gameday})

    bench = db.execute("""SELECT * FROM fbb_espn_attic 
    WHERE 
    team_id = :team_id AND 
    "fbb_espn_attic"."scoringPeriodId" = :gameday AND 
    "fbb_espn_attic"."lineupSlotId" IN (16, 17)
    ORDER BY "fbb_espn_attic"."lineupSlotId"
    """, {"team_id": team_id, "gameday": gameday})

    owner1 = db.execute("""
    SELECT * FROM "fbb_teams" WHERE team_id = :team_id  
    """, {"team_id": team_id, "gameday": gameday})

    owner2 = db.execute("""
    SELECT * FROM "fbb_teams" WHERE team_id = :team_id  
    """, {"team_id": team_id, "gameday": gameday})

    #owner = db.execute(owner, {"team_id": team_id})
    #owner_f = format_results(owner)

    #owner_name = owner_f[0]['owner']
    db.commit()

    return render_template("fbb/z3_team.html", hitters=hitters, pitchers=pitchers, bench=bench, owner1=owner1, owner2=owner2, time=time) #, owner_name=owner_name)

@app.route("/fbb/leaderboard")
def fbb_leaderboard():
    if "fbb_user" in session:
        fbb_user = session['fbb_user']
        #fbb_team_name = session['fbb_team_name']

        time = db.execute("SELECT DISTINCT * FROM fbb_espn WHERE index = 0")
        dates = db.execute("""SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ""")
        today = dates.fetchall()[0][0]

        playing_yet_test = db.execute("""SELECT "team_id_f", SUM("PA") as "PA" FROM fbb_espn WHERE 
            "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
            "fbb_espn"."PA" > 0
        GROUP BY "team_id_f"
        """)

        if playing_yet_test.rowcount == 0: 
            today_or_yest = today - 1 
            live_or_attic = "fbb_espn_attic"
        else: 
            today_or_yest = today
            live_or_attic = "fbb_espn"

        scoreboard = db.execute(f"""SELECT "team_id_f" as a, SUM("TB") as "TB", SUM("BB") as "BB", 
            SUM("R") as "R", SUM("RBI") as "RBI", SUM("SB") as "SB", 
            TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")) + (SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "OPS"
        FROM fbb_scoreboard    
        GROUP BY "team_id_f"
        HAVING SUM("AB") > 0 
        ORDER BY "OPS" DESC
        """)
            #SUM("OUTS") as "OUTS", SUM("HD"), SUM("SV"), TRUNC(SUM("SO") / (SUM("OUTS") / 3) * 9, 2) AS "KP9", TRUNC((SUM("BBag") + SUM("HA")) / (SUM("OUTS") / 3), 2) AS "WHIP", TRUNC((SUM("ERAG") * 9) / (SUM("OUTS") / 3), 2) AS "ERA"

        team_hitters = db.execute(f"""SELECT "team_id_f", SUM("PA") as "PA", SUM("AB") as AB, 
            SUM("H") as "H", SUM("1B") as "1B", SUM("2B") as "2B", SUM("3B") as "3B", SUM("HR") as "HR", 
            SUM("TB") as "TB", SUM("K") as "K", SUM("BB") as "BB", SUM("IBB") as "IBB", SUM("HBP") as "HBP", 
            SUM("R") as "R", SUM("RBI") as "RBI", SUM("SB") as "SB", SUM("CS") as "CS", 
            TRUNC(SUM("H") / SUM("AB"), 3) as "AVG", 
            TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")), 3) as "OBP",
            TRUNC(SUM("TB") / SUM("AB"), 3) as "SLG", 
            TRUNC( (((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")) + SUM("TB") / SUM("AB")), 3   ) AS "OPS"
        FROM {live_or_attic}    
        WHERE 
            {live_or_attic}."scoringPeriodId" = {today_or_yest} AND 
            {live_or_attic}."PA" > 0
        GROUP BY "team_id_f"
        HAVING SUM("AB") > 0 
        ORDER BY "OPS" DESC
        """)
        #TRUNC((SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "SLG", 
        #(SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) - {yesterday} AND 

        hitters = db.execute(f"""SELECT "team_id_f", "lineupSlotId_f", "fullName", "proTeamId_f", "PA", "AB", "H", "1B", "2B", "3B", "HR", "TB", "K", "BB", "IBB", "HBP", "R", "RBI", "SB", "CS", "AVG", "OBP", "SLG", "OPS"
        FROM {live_or_attic} 
        WHERE 
            "{live_or_attic}"."scoringPeriodId" = {today_or_yest} AND 
            "{live_or_attic}"."PA" > 0
        ORDER BY "{live_or_attic}"."OPS" DESC, "{live_or_attic}"."PA" DESC
        """)

        db.commit()
        return render_template("fbb/z3_lbd_hit.html", scoreboard=scoreboard, team_hitters=team_hitters, hitters=hitters, time=time, fbb_user=fbb_user, today_or_yest=today_or_yest, today=today) #, owner_name=owner_name)
    else:
        return redirect(url_for("fbb/fbb_login"))

@app.route("/fbb/lbd_pitch")
def fbb_lbd_pit():
    if "fbb_user" in session:
        fbb_user = session['fbb_user']
        #fbb_team_name = session['fbb_team_name']

        time = db.execute("SELECT DISTINCT * FROM fbb_espn WHERE index = 0")
        dates = db.execute("""SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ""")
        today = dates.fetchall()[0][0]

        playing_yet_test = db.execute("""SELECT "team_id_f", SUM("PA") as "PA" FROM fbb_espn WHERE 
            "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
            "fbb_espn"."PA" > 0
        GROUP BY "team_id_f"
        """)

        if playing_yet_test.rowcount == 0: 
            today_or_yest = today - 1 
            live_or_attic = "fbb_espn_attic"
        else: 
            today_or_yest = today
            live_or_attic = "fbb_espn"

        team_hitters = db.execute(f"""SELECT "team_id_f", SUM("G"), SUM("GS"), SUM("OUTS") as "OUTS", SUM("BF"), SUM("PITCH COUNT"), SUM("HA"), SUM("BBag"), 
            SUM("SO"), SUM("RA"), SUM("ERAG"), SUM("HRA"), SUM("W"), SUM("L"), SUM("QS"), SUM("HD"), SUM("SVOPP"), SUM("SV"), SUM("BS")
            ,
            TRUNC(SUM("SO") / (SUM("OUTS") / 3) * 9, 2) AS "KP9",  
            TRUNC(SUM("HA") / (SUM("BF") - SUM("BBag")), 3) AS "BAA", 
            TRUNC((SUM("BBag") + SUM("HA")) / (SUM("OUTS") / 3), 2) AS "WHIP", 
            TRUNC((SUM("HA") + SUM("BBag")) / SUM("BF"), 3) AS "OBPA",
            TRUNC((SUM("ERAG") * 9) / (SUM("OUTS") / 3), 2) AS "ERA"
        FROM {live_or_attic}    
        WHERE 
            {live_or_attic}."scoringPeriodId" = {today_or_yest} AND  
            {live_or_attic}."OUTS" > 0
        GROUP BY "team_id_f"
        """)
        #(SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) - {yesterday} AND 

        hitters = db.execute(f"""SELECT "team_id_f", "lineupSlotId_f", "fullName", "proTeamId_f", 
        "G", "GS", "OUTS", "BF", "PITCH COUNT", "HA", "BBag", "SO", "RA", "ERAG", "HRA", "W", "L", "QS", "HD", "SVOPP", "SV", "BS", "KP9", "BAA", "WHIP", "OBPA", "ERA", 
        40 + (2 * "OUTS") + "SO" - (2 *  "BBag") - (2 *  "HA") - (3 *  "RA") - (6 * "HRA")  as "Game Score"
        FROM {live_or_attic} 
        WHERE 
            "{live_or_attic}"."scoringPeriodId" = {today_or_yest} AND 
            "{live_or_attic}"."OUTS" > 0
        ORDER BY "Game Score" DESC
        """)

        db.commit()

        return render_template("fbb/z3_lbd_pitch.html", team_hitters=team_hitters, hitters=hitters, time=time, fbb_user=fbb_user, today_or_yest=today_or_yest, today=today) #, owner_name=owner_name)
    else:
        return redirect(url_for("fbb/fbb_login"))


# @app.route("/fbb/power_ranks")
# def fbb_power_ranks():
#     if "fbb_user" in session:
#         fbb_user = session['fbb_user']

#         pRanks = db.execute(f"""SELECT * FROM fbb_pr""")

#         db.commit()
#         return render_template("z3_power_ranks.html", fbb_user=fbb_user, pRanks=pRanks) #, owner_name=owner_name)
#     else:
#         return redirect(url_for("fbb/fbb_login"))

# @app.route("/fbb/power_ranks/<int:week>")
# def fbb_power_ranks_sp(week):
#     if "fbb_user" in session:
#         fbb_user = session['fbb_user']

#         pRanks = db.execute(f"""SELECT * FROM fbb_pr WHERE "fbb_pr"."Week" = :week""", {"week": week})

#         db.commit()
#         return render_template("z3_power_ranks.html", fbb_user=fbb_user, pRanks=pRanks) #, owner_name=owner_name)
#     else:
#         return redirect(url_for("fbb/fbb_login"))

# @app.route("/fbb/free_agents/<int:period>")
# def fbb_fas(period):
#     if "fbb_user" in session:
#         fbb_user = session['fbb_user']
#         #fbb_team_name = session['fbb_team_name']

#         if period == 7: 
#             this_table = "fbb_batters_07"
#             page_type  = "Last 7 Days"
#         elif period == 14:
#             this_table = "fbb_batters_14"
#             page_type  = "Last 14 Days"
#         elif period == 28:
#             this_table = "fbb_batters_28"
#             page_type  = "Last 28 Days"
#         else: 
#             this_table = "fbb_batters_99"
#             page_type  = "2021"

#         fa_batters = db.execute(f"""SELECT "fullName", SUM("PA") as "PA", SUM("AB") as AB, 
#             SUM("H") as "H", SUM("1B") as "1B", SUM("2B") as "2B", SUM("3B") as "3B", SUM("HR") as "HR", 
#             SUM("TB") as "TB", SUM("K") as "K", SUM("BB") as "BB", SUM("IBB") as "IBB", SUM("HBP") as "HBP", 
#             SUM("R") as "R", SUM("RBI") as "RBI", SUM("SB") as "SB", SUM("CS") as "CS", 
#             TRUNC(SUM("H") / SUM("AB"), 3) as "AVG", 
#             TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")), 3) as "OBP",
#             TRUNC((SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "SLG", 
#             TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")) + (SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "OPS"
#         FROM {this_table}   
#         WHERE "{this_table}"."AB" > 0 AND 
#         "{this_table}"."playerId" NOT IN (SELECT "fbb_espn"."playerId" FROM "fbb_espn")
#         GROUP BY "fullName"
#         ORDER BY "OPS" DESC
#         """)

#         db.commit()

#         return render_template("fbb/z3_free_agents.html", fa_batters=fa_batters, page_type=page_type) #, owner_name=owner_name)
#     else:
#         return redirect(url_for("fbb/fbb_login"))

# @app.route("/fbb/leaderboard/<int:gameday>")
# def fbb_leaderboard_specific(gameday):

#     if "fbb_user" in session:
#         time = db.execute("SELECT DISTINCT * FROM fbb_espn WHERE index = 0")
#         dates = db.execute("""SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ""")
#         today = dates.fetchall()[0][0]
#         fbb_user = session['fbb_user']

#         team_hitters = db.execute("""SELECT "team_id_f", SUM("PA") as "PA", SUM("AB") as AB, 
#             SUM("H") as "H", SUM("1B") as "1B", SUM("2B") as "2B", SUM("3B") as "3B", SUM("HR") as "HR", 
#             SUM("TB") as "TB", SUM("K") as "K", SUM("BB") as "BB", SUM("IBB") as "IBB", SUM("HBP") as "HBP", 
#             SUM("R") as "R", SUM("RBI") as "RBI", SUM("SB") as "SB", SUM("CS") as "CS", 
#             TRUNC(SUM("H") / SUM("AB"), 3) as "AVG", 
#             TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")), 3) as "OBP",
#             TRUNC((SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "SLG", 
#             TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")) + (SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "OPS"
#         FROM fbb_espn_attic
#         WHERE 
#             "fbb_espn_attic"."scoringPeriodId" = :gameday AND 
#             "fbb_espn_attic"."PA" > 0
#         GROUP BY "team_id_f"
#         ORDER BY "OPS" DESC
#         """, {"gameday": gameday})

#         live_or_attic = "fbb_espn_attic"
#         today_or_yest = gameday

#         hitters = db.execute(f"""SELECT "team_id_f", "lineupSlotId_f", "fullName", "proTeamId_f", "PA", "AB", "H", "1B", "2B", "3B", "HR", "TB", "K", "BB", "IBB", "HBP", "R", "RBI", "SB", "CS", "AVG", "OBP", "SLG", "OPS"
#         FROM {live_or_attic} 
#         WHERE 
#             "{live_or_attic}"."scoringPeriodId" = {today_or_yest} AND 
#             "{live_or_attic}"."PA" > 0
#         ORDER BY "{live_or_attic}"."OPS" DESC, "{live_or_attic}"."PA" DESC
#         """)

#         db.commit()

#         return render_template("fbb/z3_lbd_hit.html", team_hitters=team_hitters, hitters=hitters, time=time, dates=dates, fbb_user=fbb_user, today_or_yest=gameday, today=today)
#     else:
#         return redirect(url_for("fbb/fbb_login"))


if __name__ == '__main__':
    app.run()
