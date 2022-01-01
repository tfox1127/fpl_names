import random, os
import pandas as pd
from datetime import datetime as dt
import datetime as dtt
from flask import Flask, render_template, request, session, redirect, url_for
from requests import NullHandler
from sqlalchemy import create_engine
from sqlalchemy import exc
from sqlalchemy.orm import scoped_session, sessionmaker
import api_check

app = Flask(__name__)
#ENV = 'dev'

#DATABASE_URL
DATABASE_URL = os.environ['DATABASE_URL']
DATABASE_URL = DATABASE_URL.replace("s://", "sql://", 1)

engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
db = scoped_session(sessionmaker(bind=engine))
app.secret_key = 'pizza'

#CURRENT_WEEK = 9
CURRENT_WEEK, FIRST_UNFINISHED_WEEK = api_check.pull_current_week()
#CURRENT_WEEK = 21
#FIRST_UNFINISHED_WEEK = 21

@app.route('/')
def index():
    elements = db.execute("""SELECT post_number, header, body FROM fpl_blog ORDER BY post_number DESC LIMIT 10""")
    db.commit()
    return render_template('index.html', elements=elements)

@app.route('/live')
def live():
    #CHECK FOR MESSAGES 
    messages = db.execute("""SELECT "message" FROM "fpl_messages" WHERE "page" = 'live' ORDER BY "id" DESC LIMIT 1 """)
    message = messages.fetchall()
    message = message[0][0]      
    if message == "None": 
        has_message = "No"
    else: 
        has_message = "Yes"

    #GET TIME FOR HEADER 
    time = db.execute("SELECT DISTINCT * FROM ftbl_live_notro WHERE entry = 129150")

    #MAIN TABLE 
    elements = db.execute("""
        SELECT * FROM 
        (SELECT * FROM "ftbl_live_notro") as scoreboard
            LEFT JOIN  
            (SELECT "element_id" as "c_id", sum("points" - "bonus" + "t_bonus") as "c_pts", sum("minutes") as "c_mins"
            FROM "ftbl_elli2"
            GROUP BY "element_id") as c_points
            ON scoreboard.cap_id = c_points.c_id
                LEFT JOIN 
                (SELECT "element_id" as "vc_id", sum("points" - "bonus" + "t_bonus") as "vc_pts", sum("minutes") as "vc_mins"
                FROM "ftbl_elli2"
                GROUP BY "element_id") as vc_points
                ON scoreboard.vp_id = vc_points.vc_id
        ORDER BY rank_live
    """)

    #LAST MAN STANDING 
    bottoms =  db.execute("""SELECT "entry_name", "played", "price_played", "score", "Captain", "Vice Captain" 
                            FROM ftbl_live_notro WHERE entry not in (SELECT \"Team ID\" FROM \"lms_el\" 
                            WHERE \"Team ID\" IS NOT NULL)  ORDER BY score LIMIT 5 """)
                            
    groups = db.execute(f"""SELECT 
                        "Team 1 ID", "Team 1 Name", "score_1", "price_played_1",
                        "Team 2 ID", "Team 2 Name", "score_2", "price_played_2",
                        "Group"
                        FROM 
        (SELECT "Group", "Team 1 ID", "Team 2 ID", "Team 1 Name", "Team 2 Name" FROM tbl_2122_groups WHERE "GW" = {CURRENT_WEEK}) as GROUPS
        LEFT JOIN 
            (SELECT "entry" as entry_1, "score" as score_1, "price_played" as price_played_1 FROM "ftbl_live_notro") as SCOREBOARD_1
                ON GROUPS."Team 1 ID" = SCOREBOARD_1.entry_1
        LEFT JOIN 
            (SELECT "entry" as entry_2, "score" as score_2, "price_played" as price_played_2 FROM "ftbl_live_notro") as SCOREBOARD_2
                ON GROUPS."Team 2 ID" = SCOREBOARD_2.entry_2
        ORDER BY "Group"
        """)

    #PREMIRE LEAGUE SCOREBOARD 
    epls =  db.execute("SELECT * FROM \"ftbl_scoreboard2\" ORDER BY \"minutes_game\" DESC, \"id\" LIMIT 50")

    #ACTIVE GAMES 
    actives = db.execute("""
        SELECT * FROM 
            (SELECT * FROM "ftbl_elli2") as a
            LEFT JOIN 
                (SELECT "id", "finished"
                FROM "fpl_picks_schedule") as b 
                on a.fixture = b.id
                WHERE "finished" = False 
                AND ((minutes > 0 AND minutes_game < 60 AND points > 1) 
                or (minutes > 60 AND points > 2) or t_bonus > 0) 
        ORDER BY BPS DESC 
    """) 

    #SCORE SHEET 
    sss = db.execute("""
        SELECT "a"."element_id", "a"."web_name", "a"."team_name", "a"."goals_scored", 
            "a"."assists", "b"."team_h_name", "b"."team_a_name", "c"."owner", "a"."minutes", 
            "a"."minutes_game", "a"."t_bonus", "a"."points"
        FROM "ftbl_elli2" as "a"
        LEFT JOIN "ftbl_scoreboard2" as "b" on "a"."fixture" = "b"."id" 
        LEFT JOIN "df_owners" as "c" on "a"."element_id" = "c"."element_id"
        WHERE "goals_scored" > 0 OR "assists" > 0
        ORDER BY "a"."fixture"
    """)

    db.commit()
    return render_template('live.html', has_message=has_message, message=message, elements=elements, time=time, epls=epls, actives=actives, sss=sss, bottoms=bottoms, groups=groups)

@app.route('/cup_matchup/<int:cup_matchup_id>')
def cup_matchup(cup_matchup_id):
    cups = db.execute(f"""SELECT "Group", "Match", "l21"."score" as "Team 1 Score", "l22"."score" as "Team 2 Score", "Match ID" FROM "Cup"
        LEFT JOIN "ftbl_live_notro" as "l21" on "Cup"."Team 1 ID" = "l21"."entry"
        LEFT JOIN "ftbl_live_notro" as "l22" on "Cup"."Team 2 ID" = "l22"."entry"
        WHERE "GW" = (SELECT * FROM "tbl_GW" limit 1)
        ORDER BY "Group"
        """)
    cups2 = db.execute(f"""SELECT "Group", "Match", "l21"."score" as "Team 1 Score", "l22"."score" as "Team 2 Score", "Match ID" FROM "Cup"
        LEFT JOIN "ftbl_live_notro" as "l21" on "Cup"."Team 1 ID" = "l21"."entry"
        LEFT JOIN "ftbl_live_notro" as "l22" on "Cup"."Team 2 ID" = "l22"."entry"
        WHERE "GW" = (SELECT * FROM "tbl_GW" limit 1)
        ORDER BY "Group"
        """)

    elements = db.execute(f"""SELECT * FROM "ftbl_teams30" WHERE \"entry\" in
        (SELECT "Team 1 ID" as "entry"
        FROM "Cup"
        WHERE "Match ID" = {cup_matchup_id} AND "GW" = (SELECT * FROM "tbl_GW" limit 1)
        UNION
        SELECT "Team 2 ID" as "entry"
        FROM "Cup"
        WHERE "Match ID" = {cup_matchup_id} AND "GW" = (SELECT * FROM "tbl_GW" limit 1))
        """)
    db.commit()
    return render_template('cup_matchup.html', cups=cups, cups2=cups2, elements=elements, cup_matchup_id=cup_matchup_id)

@app.route('/datatest')
def datatest():
    d = db.execute("""SELECT * FROM ftbl_live_notro""")
    db.commit()
    df = pd.DataFrame(d.fetchall(), columns=d.keys())
    #test = df.to_html(classes='table table-sm text-xsmall table-hover sortable;')
    test = df.to_csv()

    return render_template('datatest.html', test=test, tables=[df.to_html(classes='table-sm text-xsmall table-hover sortable')], titles=df.columns.values)

@app.route('/elli')
def elli():
    #ellis = db.execute("SELECT * FROM ftbl_elli2 WHERE ownership != '0.0%' ORDER BY score DESC")
    ellis = db.execute("""
    SELECT * FROM ftbl_elli2
    LEFT JOIN owners_pct ON ftbl_elli2.element_id = owners_pct.element
    WHERE ownership != '0.0%' 
    ORDER BY points DESC""")
    
    #nonellis = db.execute("SELECT * FROM ftbl_elli2 WHERE ownership = '0.0%' ORDER BY score DESC LIMIT 15")
    nonellis = db.execute("""
        SELECT * FROM ftbl_elli2
        LEFT JOIN owners_pct ON ftbl_elli2.element_id = owners_pct.element
        WHERE ownership is NULL
        ORDER BY points DESC
        LIMIT 15""")
    db.commit()

    return render_template('elli.html', ellis=ellis, nonellis=nonellis)

@app.route("/player/<int:player_id>")
def players(player_id):
  headers    = db.execute("SELECT * FROM eplayer_info WHERE id = :player_id", {"player_id": player_id})
  players    = db.execute("SELECT * FROM df_phistory WHERE element = :player_id", {"player_id": player_id})
  owners     = db.execute("SELECT * FROM df_owner_info WHERE element = :player_id", {"player_id": player_id})
  db.commit()
  
  return render_template("epl_player.html", headers=headers, players=players, owners=owners)

@app.route("/teams30/<int:team_id>")
def teams30(team_id):
  pname    = db.execute("SELECT * FROM ftbl_live_notro WHERE entry = :team_id", {"team_id": team_id})
  elements = db.execute("SELECT * FROM ftbl_teams30 WHERE \"entry\" = :entry", {"entry": team_id})
  db.commit()
  return render_template("team30.html", elements=elements, pname=pname)

@app.route("/epl_fixture/<int:fixture_id>")
def epl_fixture(fixture_id):
    elements = db.execute("SELECT * FROM ftbl_elli2 WHERE \"fixture\" = :fixture_id AND \"minutes\" > 0 ORDER BY BPS DESC ", {"fixture_id": fixture_id})
    db.commit()
    return render_template("epl_fixture.html", elements=elements)

@app.route('/lms')
def lms():
    acti = db.execute("SELECT * FROM lms_ac")
    elim = db.execute("SELECT * FROM lms_el")
    db.commit()
    return render_template('lms.html', acti=acti, elim=elim)

@app.route('/lcs')
def lcs():
    return render_template('lcs.html')

@app.route('/cups')
def cups():
    return render_template('cups.html')

@app.route('/cup_summary')
def cup_summary():

    table_a = db.execute("SELECT * FROM tbl_cup_table WHERE \"Group\" = 'A'")
    table_b = db.execute("SELECT * FROM tbl_cup_table WHERE \"Group\" = 'B'")
    table_c = db.execute("SELECT * FROM tbl_cup_table WHERE \"Group\" = 'C'")
    table_d = db.execute("SELECT * FROM tbl_cup_table WHERE \"Group\" = 'D'")
    table_e = db.execute("SELECT * FROM tbl_cup_table WHERE \"Group\" = 'E'")

    seeds = db.execute("SELECT * FROM tbl_cup_seeds")

    db.commit()
    
    return render_template('cup_summary.html', table_a=table_a, table_b=table_b, table_c=table_c, table_d=table_d, table_e=table_e, seeds=seeds)

@app.route('/hof')
def hof():
    elements = db.execute('SELECT * FROM hof_rk ORDER BY "Overall" DESC LIMIT 50').fetchall()
    champs   = db.execute('SELECT * FROM hof_ch').fetchall()
    db.commit()
    return render_template('hof.html', elements=elements, champs = champs)

@app.route('/run_search', methods= ['POST'])
def run_search():
    if request.method == 'POST':
        search_for = request.form['search_for']
        search_for_like = "%" + search_for + "%"
        elements = db.execute("SELECT * FROM ftbl_elli2 WHERE UPPER(ftbl_elli2.\"web_name\") LIKE UPPER(:search_for_like) OR UPPER(\"ftbl_elli2\".\"team_name\") LIKE UPPER(:search_for_like)", {"search_for_like":search_for_like})
        db.commit()
        return render_template('search_results.html', elements=elements, search_for=search_for)

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
    return redirect(f'/picks/make_picks/{FIRST_UNFINISHED_WEEK}')
    #return redirect(url_for(make_picks_router))

@app.route('/picks/make_picks/<int:gameweek>')
def make_picks(gameweek): 
    
    #print("browser time: ", request.args.get("time"))

    #print("server time : ", time.strftime('%A %B, %d %Y %H:%M:%S'));
    asdf = dtt.datetime.now()

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
        ts_now = dt.now()

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

##################################################################
#NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES 
#NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES 
def format_results(result):
    d, a = {}, []
    for rowproxy in result:
        for column, value in rowproxy.items():
            d = {**d, **{column: value}}
        a.append(d)
    return a

@app.route("/names")
def landing():
    if 'user' in session:
        return redirect(url_for("profile", user=session['user']))

    else:
        return render_template("/names/z2_landing.html")

@app.route("/names/login", methods = ["POST", "GET"])
def login():
    if request.method == "POST":
        user = request.form["name"]
        session['user'] = user

        q = """SELECT user_name FROM z_users WHERE user_id = (SELECT partner FROM z_users WHERE user_name = :user)"""
        partners = db.execute(q, {"user": session['user']})
        db.commit()
        partner = partners.fetchall()

        try: 
            session['partner'] = partner[0][0]
        except: 
            session['partner'] = "unavailable"

        return redirect(url_for("profile", user=session['user'], partner=session['partner']))
    else:
        return render_template("/names/z2_login.html")

@app.route("/names/logout", methods = ["POST", "GET"])
def logout():

    session.pop('user')
    session.pop('partner')
    db.remove()

    return redirect(url_for("login"))

@app.route("/names/profile")
def profile_redir():
    if 'user' in session: 
        return redirect(f"/names/profile/{session['user']}")
    else:
        return render_template("/names/z2_login.html")

@app.route("/names/profile/<string:user>")
def profile(user):
    if 'user' in session: 
        return render_template("/names/z2_profile.html", user=session['user'], partner=session['partner'])
    else:
        return render_template("/names/z2_login.html")

@app.route("/names/profile/<string:user>/list/<string:list_type>")
def user_ratings(user, list_type):
    user_summary = db.execute("""
            SELECT CAST("wuser"."Rating" AS INTEGER), COUNT("wuser"."User") as Count FROM 
            (
                                SELECT ratings_recent.*, ratings_all.* FROM 
                                (   SELECT "2020 Rank", "User", MAX("id") as "MID"
                                    FROM "z_ratings"
                                    GROUP BY "2020 Rank", "User"
                                ) as ratings_recent 
                                LEFT JOIN 
                                (   SELECT "id", "Rating"
                                    FROM "z_ratings"
                                ) as ratings_all
                                ON ratings_recent."MID" = ratings_all."id"
                                ) as wuser
            WHERE "wuser"."User" = :user
            GROUP BY "wuser"."Rating"
            """, {"user":user})
    db.commit()

    if list_type == 'all': 
        
        user_ratings = db.execute("""
            SELECT wuser."2020 Rank", names."Name", CAST(wuser."Rating" AS INTEGER) as "Your Rating"  FROM 
                (
                    SELECT ratings_recent.*, ratings_all.* FROM 
                    (   SELECT "2020 Rank", "User", MAX("id") as "MID"
                        FROM "z_ratings"
                        GROUP BY "2020 Rank", "User"
                    ) as ratings_recent 
                    LEFT JOIN 
                    (   SELECT "id", "Rating"
                        FROM "z_ratings"
                    ) as ratings_all
                    ON ratings_recent."MID" = ratings_all."id"
                    WHERE ratings_recent."User" = :user
                    ) as wuser
                LEFT JOIN
                    (SELECT "2020 Rank", "Name" FROM z_src_name_list) as names
                    ON wuser."2020 Rank" = names."2020 Rank" 
            WHERE wuser."User" = :user """, {"user" : session['user']})
        db.commit()
    else: 
        
        user_ratings = db.execute("""
            SELECT wuser."2020 Rank", names."Name", CAST(wuser."Rating" AS INTEGER) as "Your Rating"  FROM 
                (
                    SELECT ratings_recent.*, ratings_all.* FROM 
                    (   SELECT "2020 Rank", "User", MAX("id") as "MID"
                        FROM "z_ratings"
                        GROUP BY "2020 Rank", "User"
                    ) as ratings_recent 
                    LEFT JOIN 
                    (   SELECT "id", "Rating"
                        FROM "z_ratings"
                    ) as ratings_all
                    ON ratings_recent."MID" = ratings_all."id"
                    WHERE ratings_recent."User" = :user
                    ) as wuser
                LEFT JOIN
                    (SELECT "2020 Rank", "Name" FROM z_src_name_list) as names
                    ON wuser."2020 Rank" = names."2020 Rank" 
            WHERE wuser."User" = :user 
            AND wuser."Rating" = :list_type """, {"user":user, "list_type": list_type})
        db.commit()

    return render_template("names/z2_user_ratings.html", user=user, list_type = list_type, user_ratings=user_ratings, user_summary=user_summary)

@app.route("/names/compare/<string:list_type>")
def compare(list_type):
    if "user" in session:
        list_types = {   
        'all' : "",
        'full': """ AND wuser."Rating" = 3 AND wpartner."Rating" = 3""", 
        'partial': """ AND wuser."Rating" > 1 AND wpartner."Rating" > 1""", 
        'veto_u' : """ AND wuser."Rating" = 1 AND wpartner."Rating" > 1""", 
        'veto_p': """ AND wuser."Rating" > 1 AND wpartner."Rating" = 1"""}
        
        list_types_f = {   
        'all' : "All Name Options",
        'full': "Full Matches", 
        'partial': "Partial Matches", 
        'veto_u' : "Vetoed by You", 
        'veto_p': "Vetoed by Partner" }

        title = list_types_f[list_type]

        compare = db.execute("""SELECT wuser."2020 Rank", names."Name", CAST(wuser."Rating" as INTEGER) as "Your Rating" , CAST(wpartner."Rating" as INTEGER) as "Partner's Rating" FROM 
            (SELECT ratings_recent.*, ratings_all.* FROM 
            (SELECT "2020 Rank", "User", MAX("id") as "MID"
            FROM "z_ratings"
            GROUP BY "2020 Rank", "User") as ratings_recent 
            LEFT JOIN 
            (SELECT "id", "Rating"
            FROM "z_ratings") as ratings_all
            ON ratings_recent."MID" = ratings_all."id"
            WHERE ratings_recent."User" = :user) as wuser
            LEFT JOIN
            (SELECT ratings_recent.*, ratings_all.* FROM 
            (SELECT "2020 Rank", "User", MAX("id") as "MID"
            FROM "z_ratings"
            GROUP BY "2020 Rank", "User") as ratings_recent 
            LEFT JOIN 
            (SELECT "id", "Rating"
            FROM "z_ratings") as ratings_all
            ON ratings_recent."MID" = ratings_all."id"
            WHERE ratings_recent."User" = :partner) as wpartner
            ON wuser."2020 Rank" = wpartner."2020 Rank" 
            LEFT JOIN
            (SELECT "2020 Rank", "Name" FROM z_src_name_list) as names
            ON wuser."2020 Rank" = names."2020 Rank" 
            WHERE 
            wuser."User" = :user AND 
            wpartner."User" = :partner """ + list_types[list_type],  {"user" : session['user'], "partner" : session['partner']})

        db.commit()
    
        return render_template('/names/z2_compare.html', compare=compare, title=title)
    else:
        return redirect(url_for("login"))

@app.route("/names/random_name")
def random_name():
    if "user" in session:
        #get list of unrated names
        user = session["user"]

        q = """SELECT a."2020 Rank"
            FROM (SELECT z_src_name_list.*
            FROM z_src_name_list) as a
            LEFT JOIN (
            SELECT z_ratings.*
            FROM z_ratings WHERE z_ratings."User" = :user ) as b
            ON a."2020 Rank" = b."2020 Rank"
            WHERE b."User" IS NULL"""

        undone = db.execute(q, {"user": user})
        db.commit()
        undone = undone.fetchall()

        todo = len(undone)

        if todo == 0: 
            return redirect(url_for("profile_redir"))
        else: 
            undone[random.choice(range(todo))][0]
            pick = undone[0][0]
            
            #run query to get that picks info
            q = "SELECT * FROM z_src_name_list WHERE \"2020 Rank\" = :pick"
            names = db.execute(q, {"pick": pick})
            db.commit()
            names = names.fetchall()
            #f_names = format_results(names)
            f_rank = names[0][1]
            f_name = names[0][2]

            session['name'] = f_name
            session['rank'] = f_rank

            return redirect(url_for("name_page", name=session['name']))
    else:
        return redirect(url_for("login"))

@app.route('/names/<string:name>')
def name_page(name):

    name_combo = db.execute("""SELECT a.*, b."Rating" as "Tommy",  c."Rating" as "Michelle"
            FROM (SELECT z_src_name_list.*
            FROM z_src_name_list) as a

            LEFT JOIN (
            SELECT z_ratings.*
            FROM z_ratings WHERE z_ratings."User" = :user ) as b
            ON a."2020 Rank" = b."2020 Rank"

            LEFT JOIN (
            SELECT z_ratings.*
            FROM z_ratings WHERE z_ratings."User" = :partner ) as c
            ON a."2020 Rank" = c."2020 Rank"

            WHERE a."Name" = :name """, {"name" : name, "user" : session['user'], "partner" : session['partner']})
    db.commit()
    name_combo = name_combo.fetchall()

    name = name
    rank = name_combo[0][1]
    rate_u = name_combo[0][3]
    rate_p = name_combo[0][4]

    return render_template('names/z2_name.html', user=session['user'], name=name, rank=rank, rate_u= rate_u, rate_p= rate_p)

@app.route('/names/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        x = request.form['rank']
        y = request.form['user']
        z = request.form['rating']

        db.execute("INSERT INTO z_ratings (\"2020 Rank\", \"User\", \"Rating\") VALUES (:x, :y, :z)", {"x": x, "y": y, "z": z})
        #db.execute("UPDATE name_list_g SET \"Michelle\" = (:x) WHERE \"Name\" = (:y)", {"x": x, "y":y})
        db.commit()
        #return redirect(request.referrer)
        return redirect(url_for("random_name"))

@app.route('/names/search_name')
def search_name():

    return render_template('names/z2_search.html')

@app.route("/names/search_name_results", methods = ["POST", "GET"])
def search_name_results():
    if request.method == 'POST':
        search_for_name = request.form['search_for_name']
        search_for_name_like = "%" + search_for_name + "%"
        #search_results_data = db.execute("""SELECT * FROM z_src_name_list WHERE UPPER("Name") LIKE UPPER(:search_for_name_like)""", {"search_for_name_like":search_for_name_like})
        search_results_data = db.execute("""
            SELECT wuser."2020 Rank", names."Name", CAST(wuser."Rating" as INTEGER) as "Your Rating" , CAST(wpartner."Rating" as INTEGER) as "Partner's Rating" FROM 
                (SELECT ratings_recent.*, ratings_all.* FROM 
                (SELECT "2020 Rank", "User", MAX("id") as "MID"
                FROM "z_ratings"
                GROUP BY "2020 Rank", "User") as ratings_recent 
                LEFT JOIN 
                (SELECT "id", "Rating"
                FROM "z_ratings") as ratings_all
                ON ratings_recent."MID" = ratings_all."id"
                WHERE ratings_recent."User" = :user) as wuser
            LEFT JOIN
                (SELECT ratings_recent.*, ratings_all.* FROM 
                (SELECT "2020 Rank", "User", MAX("id") as "MID"
                FROM "z_ratings"
                GROUP BY "2020 Rank", "User") as ratings_recent 
                LEFT JOIN 
                (SELECT "id", "Rating"
                FROM "z_ratings") as ratings_all
                ON ratings_recent."MID" = ratings_all."id"
                WHERE ratings_recent."User" = :partner) as wpartner
            ON wuser."2020 Rank" = wpartner."2020 Rank" 
            LEFT JOIN
            (SELECT "2020 Rank", "Name" FROM z_src_name_list) as names
            ON wuser."2020 Rank" = names."2020 Rank" 
            WHERE UPPER("Name") LIKE UPPER(:search_for_name_like) """, {"search_for_name_like":search_for_name_like, "user" : session['user'], "partner" : session['partner']})
        db.commit()
        return render_template("names/z2_search_name_results.html", search_results_data=search_results_data, search_for_name=search_for_name)

@app.route("/names/signup", methods = ["POST", "GET"])
def signup():
    if request.method == "POST":
        user = request.form["name"]
        session['user'] = user
        return redirect(url_for("profile", user=user))
    else:
        return render_template("/names/z2_signup.html")

if __name__ == '__main__':
    app.run()


            # ,
            # TRUNC(SUM("SO") / (SUM("OUTS") / 3) * 9, 2) AS "KP9",  
            # TRUNC(SUM("HA") / (SUM("BF") - SUM("BBag")), 3) AS "BAA", 
            # TRUNC((SUM("BBag") + SUM("HA")) / (SUM("OUTS") / 3), 2) AS "WHIP", 
            # TRUNC((SUM("HA") + SUM("BBag")) / SUM("BF"), 3) AS "OBPA",
            # TRUNC((SUM("ERAG") * 9) / (SUM("OUTS") / 3), 3) AS "ERA"
