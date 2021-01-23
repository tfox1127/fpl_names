from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
#from flask_session import Session
from send_mail import send_mail
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
import datetime as datetime
import random

app = Flask(__name__)

ENV = 'dev'

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

engine = create_engine('postgres://oqivztlextiryy:f910e63e9de02a848ecddc6941e46d9cc16b3f4cc65fd8a24475f8affea90c93@ec2-3-215-207-12.compute-1.amazonaws.com:5432/davc1l7co2fgm', isolation_level="AUTOCOMMIT")
                                                  # DATABASE_URL is an environment variable that indicates where the database lives
db = scoped_session(sessionmaker(bind=engine))    # create a 'scoped session' that ensures different users' interactions with the
                                                  # database are kept separate

app.secret_key = 'pizza'

@app.route('/')
def index():
    elements = db.execute('SELECT * FROM blog ORDER BY post_number DESC LIMIT 10')
    db.commit()
    return render_template('index.html', elements=elements)

@app.route('/live')
def live():
    time = db.execute("SELECT DISTINCT * FROM live2 WHERE entry = 142805")
    elements = db.execute("SELECT DISTINCT * FROM live2 ORDER BY points_lg DESC LIMIT 50")
    #bottoms =  db.execute("SELECT * FROM live2 where entry not in (SELECT \"Team ID\" FROM \"lms_el\" WHERE \"Team ID\" IS NOT NULL) ORDER BY rank_lv DESC LIMIT 5")

    cups = db.execute(f"""SELECT DISTINCT "Group", "Match", "l21"."tPoints" as "Team 1 Score", "l22"."tPoints" as "Team 2 Score", "Match ID" FROM "Cup"
        LEFT JOIN "live2" as "l21" on "Cup"."Team 1 ID" = "l21"."entry"
        LEFT JOIN "live2" as "l22" on "Cup"."Team 2 ID" = "l22"."entry"
        WHERE "GW" = {19}
        ORDER BY "Group"
        """)

    epls =  db.execute("SELECT DISTINCT * FROM score_board")
    sss =  db.execute("SELECT DISTINCT * FROM score_sheet")

    try:
      db.commit()
    except exc.SQLAlchemyError:
      time.sleep(2)
      pass # do something intelligent here

    db.commit()
    #time = time.item() #.datetime.strftime("%m/%d/%Y, %H:%M:%S")
    return render_template('live.html', elements=elements, time=time, cups=cups, epls=epls, sss=sss)

@app.route('/cup_matchup/<int:cup_matchup_id>')
def cup_matchup(cup_matchup_id):
    cups = db.execute(f"""SELECT "Group", "Match", "l21"."tPoints" as "Team 1 Score", "l22"."tPoints" as "Team 2 Score", "Match ID" FROM "Cup"
        LEFT JOIN "live2" as "l21" on "Cup"."Team 1 ID" = "l21"."entry"
        LEFT JOIN "live2" as "l22" on "Cup"."Team 2 ID" = "l22"."entry"
        WHERE "GW" = {19}
        ORDER BY "Group"
        """)
    cups2 = db.execute(f"""SELECT "Group", "Match", "l21"."tPoints" as "Team 1 Score", "l22"."tPoints" as "Team 2 Score", "Match ID" FROM "Cup"
        LEFT JOIN "live2" as "l21" on "Cup"."Team 1 ID" = "l21"."entry"
        LEFT JOIN "live2" as "l22" on "Cup"."Team 2 ID" = "l22"."entry"
        WHERE "GW" = {19}
        ORDER BY "Group"
        """)

    elements = db.execute(f"""SELECT * FROM "teams30" WHERE \"entry\" in
        (SELECT "Team 1 ID" as "entry"
        FROM "Cup"
        WHERE "Match ID" = {cup_matchup_id} AND "GW" = {19}
        UNION
        SELECT "Team 2 ID" as "entry"
        FROM "Cup"
        WHERE "Match ID" = {cup_matchup_id} AND "GW" = {19})
        """)
    db.commit()
    return render_template('cup_matchup.html', cups=cups, cups2=cups2, elements=elements, cup_matchup_id=cup_matchup_id)

@app.route('/elli')
def elli():
    ellis = db.execute("SELECT * FROM df_elli WHERE ownership != '0.0%' ORDER BY score DESC")
    nonellis = db.execute("SELECT * FROM df_elli WHERE ownership = '0.0%' ORDER BY score DESC LIMIT 15")
    db.commit()
    #time = time.item() #.datetime.strftime("%m/%d/%Y, %H:%M:%S")
    return render_template('elli.html', ellis=ellis, nonellis=nonellis)

@app.route('/run_search', methods= ['POST'])
def run_search():
    if request.method == 'POST':
        search_for = request.form['search_for']
        search_for_like = "%" + search_for + "%"
        search_results_data = db.execute("SELECT * FROM \"df_elli\" WHERE UPPER(\"df_elli\".\"web_name\") LIKE UPPER(:search_for_like) OR UPPER(\"df_elli\".\"team\") LIKE UPPER(:search_for_like)", {"search_for_like":search_for_like})
        #q = ("SELECT * FROM \"df_elli\" WHERE UPPER(\"df_elli\".\"web_name\") LIKE UPPER(:search_for)")
            #"src_name_list.\"2020 Rank\" = ratings.\"2020 Rank\" WHERE ratings.\"User\" != :user OR ratings.\"User\" is NULL")

        #search_results_data = db.execute(q, {"search_for" : search_for})
        db.commit()
        #return redirect(request.referrer, search_results_data=search_results_data)
        #return full
        return render_template('search_results.html', search_results_data=search_results_data, search_for=search_for)

#@app.route('/search_results')
#def search_results(search_results_data):

#     time = time.item() #.datetime.strftime("%m/%d/%Y, %H:%M:%S")
#    return render_template('search_results.html', ellis=ellis, nonellis=nonellis)

@app.route("/teams/<int:team_id>")
def teams(team_id):
  """List details about a single flight."""
  pname    = db.execute("SELECT * FROM live2 WHERE entry = :team_id", {"team_id": team_id})
  #elements = db.execute("SELECT * FROM teams2 WHERE entry = :team_id", {"team_id": team_id})
  elements = db.execute("SELECT * FROM \":team_id\"", {"team_id": team_id})
  db.commit()
  return render_template("teams.html", elements=elements, pname=pname)

@app.route("/player/<int:player_id>")
def players(player_id):
  headers    = db.execute("SELECT * FROM eplayer_info WHERE id = :player_id", {"player_id": player_id})
  players    = db.execute("SELECT * FROM df_phistory WHERE element = :player_id", {"player_id": player_id})
  owners     = db.execute("SELECT * FROM df_owner_info WHERE element = :player_id", {"player_id": player_id})
  db.commit()
  return render_template("epl_player.html", headers=headers, players=players, owners=owners)

@app.route("/teams2/<int:team_id>")
def teams2(team_id):
  """List details about a single flight."""
  pname    = db.execute("SELECT * FROM live2 WHERE entry = :team_id", {"team_id": team_id})
  #elements = db.execute("SELECT * FROM teams2 WHERE entry = :team_id", {"team_id": team_id})
  elements = db.execute("SELECT * FROM df_teams20 WHERE entry = :team_id", {"team_id": team_id})
  db.commit()
  return render_template("teams2.html", elements=elements, pname=pname)

@app.route("/teams30/<int:team_id>")
def teams30(team_id):
  """List details about a single flight."""
  pname    = db.execute("SELECT * FROM live2 WHERE entry = :team_id", {"team_id": team_id})
  elements = db.execute("SELECT * FROM teams30 WHERE \"entry\" = :entry", {"entry": team_id})
  db.commit()
  return render_template("team30.html", elements=elements, pname=pname)

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

@app.route('/leaderboard')
def leaderboard():
    return render_template('fpl_list.html')

@app.route('/hof')
def hof():
    elements = db.execute('SELECT * FROM hof_rk ORDER BY "Overall" DESC LIMIT 50').fetchall()
    champs   = db.execute('SELECT * FROM hof_ch').fetchall()
    db.commit()
    return render_template('hof.html', elements=elements, champs = champs)

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
  return render_template("z2_profile.html", user=user)

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
    return render_template('z2_name.html', user=user, name=name, rank=rank)

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
    return render_template('z2_search.html')

@app.route("/search_name_results", methods = ["POST", "GET"])
def search_name_results():
    if request.method == 'POST':
        search_for_name = request.form['search_for_name']
        search_for_name_like = "%" + search_for_name + "%"
        search_results_data = db.execute("SELECT * FROM \"df_elli\" WHERE UPPER(\"df_elli\".\"web_name\") LIKE UPPER(:search_for_name_like)", {"search_for_name_like":search_for_name_like})

        db.commit()
        return render_template("z2_search_name_results.html", search_results_data=search_results_data, search_for_name=search_for_name)


if __name__ == '__main__':
    app.run()
