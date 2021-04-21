import random, os
from flask import Flask, render_template, request, session, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy import exc
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)
ENV = 'dev'

#DATABASE_URL
DATABASE_URL = os.environ['DATABASE_URL']

engine = create_engine(DATABASE_URL, isolation_level="AUTOCOMMIT")
#engine = create_engine('postgres://oqivztlextiryy:f910e63e9de02a848ecddc6941e46d9cc16b3f4cc65fd8a24475f8affea90c93@ec2-3-215-207-12.compute-1.amazonaws.com:5432/davc1l7co2fgm', isolation_level="AUTOCOMMIT")
db = scoped_session(sessionmaker(bind=engine))
app.secret_key = 'pizza'

@app.route('/')
def index():
    elements = db.execute('SELECT * FROM blog ORDER BY post_number DESC LIMIT 10')
    db.commit()
    return render_template('index.html', elements=elements)

@app.route('/live')
def live():
    time = db.execute("SELECT DISTINCT * FROM ftbl_live_notro WHERE entry = 142805")
    #elements = db.execute("SELECT DISTINCT * FROM live2 ORDER BY points_lg DESC LIMIT 50")
    #elements = db.execute(f"""SELECT DISTINCT *, score_fix + sogw as new_live
    #        FROM live2
    #        LEFT JOIN (SELECT entry, sum(score) as "score_fix" FROM "teams30" GROUP BY entry) as scores2
    #        ON live2.entry = scores2.entry
    #        ORDER BY new_live DESC""" )

    elements = db.execute("SELECT * FROM ftbl_live_notro ORDER BY rank_live ")
    #bottoms =  db.execute("SELECT * FROM live2 where entry not in (SELECT \"Team ID\" FROM \"lms_el\" WHERE \"Team ID\" IS NOT NULL) ORDER BY rank_lv DESC LIMIT 5")

    cups = db.execute(f"""SELECT DISTINCT "Group", "Match", "l21"."score" as "Team 1 Score", "l22"."score" as "Team 2 Score", "Match ID" FROM "Cup"
        LEFT JOIN "ftbl_live_notro" as "l21" on "Cup"."Team 1 ID" = "l21"."entry"
        LEFT JOIN "ftbl_live_notro" as "l22" on "Cup"."Team 2 ID" = "l22"."entry"
        WHERE "GW" = (SELECT * FROM "tbl_GW" limit 1)
        ORDER BY "Group"
        """)

    cups = db.execute("""
        SELECT DISTINCT "Cup"."Group", "Cup"."Match", CAST("l21"."score" AS INTEGER) as "Team 1 Score", CAST("l22"."score" AS INTEGER) as "Team 2 Score", "Cup"."Match ID",
            "lw"."t2_leg1",
            "lw"."t1_leg1",
            "lw"."t2_leg1" + "l21"."score" as "A",
            "lw"."t1_leg1" + "l22"."score" as "B",
            ("lw"."t2_leg1" + "l21"."score") - ("lw"."t1_leg1" + "l22"."score") as "C" 
            FROM "Cup"
            LEFT JOIN "ftbl_live_notro" as "l21" on "Cup"."Team 1 ID" = "l21"."entry"
            LEFT JOIN "ftbl_live_notro" as "l22" on "Cup"."Team 2 ID" = "l22"."entry"
            LEFT JOIN (
            SELECT DISTINCT "Group", "Match", CAST("T2 Score" AS INTEGER) as "t2_leg1", CAST("T1 Score" AS INTEGER) as "t1_leg1", "Match ID", "Team 1 ID", "Team 2 ID" FROM "Cup"
            WHERE "GW" = (SELECT * FROM "tbl_GW" limit 1) - 1
            ) AS "lw" ON "Cup"."Team 1 ID" = "lw"."Team 2 ID"
            WHERE "GW" = (SELECT * FROM "tbl_GW" limit 1)
            ORDER BY "Cup"."Group"
            """
    )

    epls =  db.execute("SELECT * FROM \"ftbl_scoreboard2\" ORDER BY \"minutes_game\" DESC, \"id\" LIMIT 50")
    
    actives = db.execute("SELECT * FROM ftbl_elli2 WHERE minutes_game < 90 AND ((minutes > 0 AND minutes_game < 60 AND points > 1) or (minutes > 60 AND points > 2) or t_bonus > 0)  ORDER BY BPS DESC ")
    
    #sss =  db.execute("SELECT DISTINCT * FROM score_sheet ORDER BY \"Team\"")
    sss = db.execute("""
        SELECT "a"."element_id", "a"."web_name", "a"."team_name", "a"."goals_scored", "a"."assists", "b"."team_h_name", "b"."team_a_name", "c"."owner"
        FROM "ftbl_elli2" as "a"
        LEFT JOIN "ftbl_scoreboard2" as "b" on "a"."fixture" = "b"."id" 
        LEFT JOIN "df_owners" as "c" on "a"."element_id" = "c"."element_id"
        WHERE "goals_scored" > 0 OR "assists" > 0
        ORDER BY "a"."fixture"
    """)
    db.commit()
    #time = time.item() #.datetime.strftime("%m/%d/%Y, %H:%M:%S")
    return render_template('live.html', elements=elements, time=time, cups=cups, epls=epls, actives=actives, sss=sss)

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

@app.route('/active_matches')
def active_matches():
    elements = db.execute("SELECT * FROM ftbl_elli2 WHERE minutes_game < 90 AND ((minutes > 0 AND minutes_game < 60 AND points > 1) or (minutes > 60 AND points > 2) or t_bonus > 0)  ORDER BY BPS DESC ")

    db.commit()
    return render_template('active_matches.html', elements=elements)

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

#NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES 
#NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES NAMES 
def format_results(result):
    d, a = {}, []
    for rowproxy in result:
        for column, value in rowproxy.items():
            d = {**d, **{column: value}}
        a.append(d)
    return a

@app.route("/login", methods = ["POST", "GET"])
def login():
    if request.method == "POST":
        user = request.form["name"]
        session['user'] = user
        return redirect(url_for("profile", user=user))

    else:
        return render_template("z2_login.html")

@app.route("/profile/<string:user>")
def profile(user):
  return render_template("names/z2_profile.html", user=user)

@app.route("/name/random_name")
def random_name():
    if "user" in session:
        #get list of unrated names
        user = session["user"]
        q = ("SELECT src_name_list.\"2020 Rank\" FROM src_name_list LEFT JOIN ratings ON "
         "src_name_list.\"2020 Rank\" = ratings.\"2020 Rank\" WHERE ratings.\"User\" != :user OR ratings.\"User\" is NULL")
        full = db.execute(q, {"user": user})
        f_full = format_results(full)

        #pick random formatted result
        this_many = len(f_full)
        pick = random.choice(range(this_many))
        pick = f_full[pick]['2020 Rank']

        #run query to get that picks info
        q = "SELECT * FROM src_name_list WHERE \"2020 Rank\" = :pick"
        names = db.execute(q, {"pick": pick})
        f_names = format_results(names)
        f_name = f_names[0]['Name']
        f_rank = f_names[0]['2020 Rank']

        session['name'] = f_name
        session['rank'] = f_rank

        return redirect(url_for("name_page", name=session['name']))
    else:
        return redirect(url_for("login"))

@app.route('/name/<string:name>')
def name_page(name):
    user = session['user']
    name = session['name']
    rank = session['rank']
    return render_template('names/z2_name.html', user=user, name=name, rank=rank)

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        x = request.form['rank']
        y = request.form['user']
        z = request.form['rating']

        db.execute("INSERT INTO ratings (\"2020 Rank\", \"User\", \"Rating\") VALUES (:x, :y, :z)", {"x": x, "y": y, "z": z})
        #db.execute("UPDATE name_list_g SET \"Michelle\" = (:x) WHERE \"Name\" = (:y)", {"x": x, "y":y})
        db.commit()
        #return redirect(request.referrer)
        return redirect(url_for("random_name"))

@app.route('/search_name')
def search_name():
    return render_template('names/z2_search.html')

@app.route("/search_name_results", methods = ["POST", "GET"])
def search_name_results():
    if request.method == 'POST':
        search_for_name = request.form['search_for_name']
        search_for_name_like = "%" + search_for_name + "%"
        search_results_data = db.execute("SELECT * FROM \"df_elli\" WHERE UPPER(\"df_elli\".\"web_name\") LIKE UPPER(:search_for_name_like)", {"search_for_name_like":search_for_name_like})

        db.commit()
        return render_template("names/z2_search_name_results.html", search_results_data=search_results_data, search_for_name=search_for_name)

#FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB 
#FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB FBB 
@app.route("/fbb")
def fbb(): 
    return render_template('z3_fbb.html')

@app.route("/fbb/login", methods = ["POST", "GET"])
def fbb_login():
    if request.method == "POST":
        fbb_user = request.form["fbb_user"]
        session['fbb_user'] = fbb_user

        #fbb_team_name = db.execute(""" SELECT * FROM "fbb_teams" WHERE short_name = :fbb_user""", {"fbb_user" : fbb_user}) 
        #session['fbb_team_name'] = fbb_team_name
        return redirect(url_for("fbb_leaderboard", fbb_user=fbb_user)) #, fbb_team_name = fbb_team_name
    else:
        return render_template("z3_login.html")

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

    return render_template("z3_team.html", hitters=hitters, pitchers=pitchers, bench=bench, owner1=owner1, owner2=owner2, time=time) #, owner_name=owner_name)

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

    return render_template("z3_team.html", hitters=hitters, pitchers=pitchers, bench=bench, owner1=owner1, owner2=owner2, time=time) #, owner_name=owner_name)

@app.route("/fbb/leaderboard")
def fbb_leaderboard():

    fbb_user = session['fbb_user']
    #fbb_team_name = session['fbb_team_name']

    time = db.execute("SELECT DISTINCT * FROM fbb_espn WHERE index = 0")

    team_hitters = db.execute("""SELECT "team_id_f", SUM("PA") as "PA", SUM("AB") as AB, 
        SUM("H") as "H", SUM("1B") as "1B", SUM("2B") as "2B", SUM("3B") as "3B", SUM("HR") as "HR", 
        SUM("TB") as "TB", SUM("K") as "K", SUM("BB") as "BB", SUM("IBB") as "IBB", SUM("HBP") as "HBP", 
        SUM("R") as "R", SUM("RBI") as "RBI", SUM("SB") as "SB", SUM("CS") as "CS", 
        TRUNC(SUM("H") / SUM("AB"), 3) as "AVG", 
        TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")), 3) as "OBP",
        TRUNC((SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "SLG", 
        TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")) + (SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "OPS"
    FROM fbb_espn    
    WHERE 
        "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
        "fbb_espn"."PA" > 0
    GROUP BY "team_id_f"
    ORDER BY "OPS" DESC
    """)

    hitters = db.execute("""SELECT "team_id_f", "lineupSlotId_f", "fullName", "proTeamId_f", "PA", "AB", "H", "1B", "2B", "3B", "HR", "TB", "K", "BB", "IBB", "HBP", "R", "RBI", "SB", "CS", "AVG", "OBP", "SLG", "OPS"
    FROM fbb_espn 
    WHERE 
        "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
        "fbb_espn"."PA" > 0
    ORDER BY "fbb_espn"."OPS" DESC, "fbb_espn"."PA" DESC
    """)

    db.commit()

    return render_template("z3_leaderboard.html", team_hitters=team_hitters, hitters=hitters, time=time, fbb_user=fbb_user) #, owner_name=owner_name)

@app.route("/fbb/free_agents")
def fbb_fas():

    fbb_user = session['fbb_user']
    #fbb_team_name = session['fbb_team_name']

    fa_batters = db.execute("""SELECT "fullName", SUM("PA") as "PA", SUM("AB") as AB, 
        SUM("H") as "H", SUM("1B") as "1B", SUM("2B") as "2B", SUM("3B") as "3B", SUM("HR") as "HR", 
        SUM("TB") as "TB", SUM("K") as "K", SUM("BB") as "BB", SUM("IBB") as "IBB", SUM("HBP") as "HBP", 
        SUM("R") as "R", SUM("RBI") as "RBI", SUM("SB") as "SB", SUM("CS") as "CS", 
        TRUNC(SUM("H") / SUM("AB"), 3) as "AVG", 
        TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")), 3) as "OBP",
        TRUNC((SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "SLG", 
        TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")) + (SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "OPS"
    FROM fbb_batters_07   
    WHERE "fbb_batters_07"."AB" > 0
    GROUP BY "fullName"
    ORDER BY "OPS" DESC
    """)

    db.commit()

    return render_template("z3_free_agents.html", fa_batters=fa_batters) #, owner_name=owner_name)

@app.route("/fbb/leaderboard/<int:gameday>")
def fbb_leaderboard_specific(gameday):
    time = db.execute("SELECT DISTINCT * FROM fbb_espn WHERE index = 0")

    team_hitters = db.execute("""SELECT "team_id_f", SUM("PA") as "PA", SUM("AB") as AB, 
        SUM("H") as "H", SUM("1B") as "1B", SUM("2B") as "2B", SUM("3B") as "3B", SUM("HR") as "HR", 
        SUM("TB") as "TB", SUM("K") as "K", SUM("BB") as "BB", SUM("IBB") as "IBB", SUM("HBP") as "HBP", 
        SUM("R") as "R", SUM("RBI") as "RBI", SUM("SB") as "SB", SUM("CS") as "CS", 
        TRUNC(SUM("H") / SUM("AB"), 3) as "AVG", 
        TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")), 3) as "OBP",
        TRUNC((SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "SLG", 
        TRUNC(((SUM("H") + SUM("BB") + SUM("HBP"))  / SUM("PA")) + (SUM("1B") + (SUM("2B") * 2) + (SUM("3B") * 3) + (SUM("HR") * 4)) / SUM("AB"), 3) as "OPS"
    FROM fbb_espn_attic
    WHERE 
        "fbb_espn_attic"."scoringPeriodId" = :gameday AND 
        "fbb_espn_attic"."PA" > 0
    GROUP BY "team_id_f"
    ORDER BY "OPS" DESC
    """, {"gameday": gameday})


    hitters = db.execute("""SELECT * FROM fbb_espn 
    WHERE 
        "fbb_espn"."scoringPeriodId" = (SELECT max("squ"."scoringPeriodId") FROM fbb_espn as squ) AND 
        "fbb_espn"."PA" > 0
    ORDER BY "fbb_espn"."OPS" DESC, "fbb_espn"."PA" DESC
    """)

    db.commit()

    return render_template("z3_leaderboard.html", team_hitters=team_hitters, hitters=hitters, time=time) #, owner_name=owner_name)

if __name__ == '__main__':
    app.run()
