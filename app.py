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
    time = db.execute("SELECT * FROM live2 WHERE entry = 142805")
    elements = db.execute("SELECT * FROM live2 ORDER BY points_lg DESC LIMIT 50")
    #bottoms =  db.execute("SELECT * FROM live2 where player_name not in (SELECT name FROM \"LMS\") ORDER BY live2.tPoints LIMIT 5")
    #bottoms =  db.execute("SELECT * FROM live2 where player_name not in (SELECT name FROM \"LMS\") ORDER BY rank_lv DESC LIMIT 5")
    bottoms =  db.execute("SELECT * FROM live2 where entry not in (SELECT \"Team ID\" FROM \"lms_el\" WHERE \"Team ID\" IS NOT NULL) ORDER BY rank_lv DESC LIMIT 5")
    epls =  db.execute("SELECT * FROM score_board")
    sss =  db.execute("SELECT * FROM score_sheet")

    try:
      db.commit()
    except exc.SQLAlchemyError:
      time.sleep(2)
      pass # do something intelligent here

    db.commit()
    #time = time.item() #.datetime.strftime("%m/%d/%Y, %H:%M:%S")
    return render_template('live.html', elements=elements, time=time, bottoms=bottoms, epls=epls, sss=sss)

@app.route('/elli')
def elli():
    ellis = db.execute("SELECT * FROM df_elli WHERE ownership != '0.0%' ORDER BY score DESC")
    nonellis = db.execute("SELECT * FROM df_elli WHERE ownership = '0.0%' ORDER BY score DESC LIMIT 15")
    db.commit()
    #time = time.item() #.datetime.strftime("%m/%d/%Y, %H:%M:%S")
    return render_template('elli.html', ellis=ellis, nonellis=nonellis)

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

@app.route("/login", methods = ["POST", "GET"])
def login():
    if request.method == "POST":
        user = request.form["name"]
        session['user'] = user
        return redirect(url_for("random"))

    else:
        return render_template("login.html")


def format_results(result):
    d, a = {}, []
    for rowproxy in result:
        for column, value in rowproxy.items():
            d = {**d, **{column: value}}
        a.append(d)
    return a

@app.route("/name/random_name")
def random_name():
    if "user" in session:
        #get list of unrated names
        user = session["user"]
        q = "SELECT src_name_list.\"2020 Rank\" FROM src_name_list LEFT JOIN ratings ON src_name_list.\"2020 Rank\" = ratings.\"2020 Rank\" WHERE ratings.\"User\" != :user OR ratings.\"User\" is NULL"
        full = db.execute(q, {"user": user})
        f_full = format_results(full)

        #pick random formatted result
        this_many = len(f_full)
        pick = random.choice(range(this_many))

        #run query to get that picks info
        q = "SELECT * FROM src_name_list WHERE \"2020 Rank\" = :pick"
        names = db.execute(q, {"pick": pick})
        f_names = format_results(names)
        f_name = f_names[0]['Name']
        f_rank = f_names[0]['2020 Rank']

        return render_template("random_name.html", user=user, name=f_name, rank=f_rank)
    else:
        return redirect(url_for("login"))

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        x = request.form['rank']
        y = request.form['user']
        z = request.form['rating']

        db.execute("INSERT INTO ratings (\"2020 Rank\", \"User\", \"Rating\") VALUES (:x, :y, :z)", {"x": x, "y": y, "z": z})
        #db.execute("UPDATE name_list_g SET \"Michelle\" = (:x) WHERE \"Name\" = (:y)", {"x": x, "y":y})
        db.commit()
        return redirect(request.referrer)

# @app.route("/m/name/random")
# def m_name_rand():
#     unrated = "FIND ONE"
#     while unrated != None:
#         picked = random.choice(range(1000))
#         name = db.execute("SELECT * FROM name_list_g WHERE \"2020 Rank\" = :picked", {"picked": picked})
#         d, a = {}, []
#         for rowproxy in name:
#             for column, value in rowproxy.items():
#                 d = {**d, **{column: value}}
#             a.append(d)
#         name = a[0]['Name']
#         rank = a[0]['2020 Rank']
#         unrated = a[0]['Michelle']
#
#     db.commit()
#
#     return render_template("name.html", unrated=unrated, name = name, rank=rank)
#
# @app.route("/t/name/random")
# def t_name_rand():
#     unrated = "FIND ONE"
#     while unrated != None:
#         picked = random.choice(range(1000))
#         name = db.execute("SELECT * FROM name_list_g WHERE \"2020 Rank\" = :picked", {"picked": picked})
#         d, a = {}, []
#         for rowproxy in name:
#             for column, value in rowproxy.items():
#                 d = {**d, **{column: value}}
#             a.append(d)
#         name = a[0]['Name']
#         rank = a[0]['2020 Rank']
#         unrated = a[0]['Tommy']
#
#     db.commit()
#
#     return render_template("name_t.html", unrated=unrated, name = name, rank=rank)
#
# @app.route('/submit_t', methods=['POST'])
# def submit_t():
#     if request.method == 'POST':
#         x = request.form['rating']
#         y = request.form['name']
#         db.execute("INSERT INTO name_log (\"rating\") VALUES (:x)", {"x": y})
#         db.execute("UPDATE name_list_g SET \"Tommy\" = (:x) WHERE \"Name\" = (:y)", {"x": x, "y":y})
#         db.commit()
#         return redirect(request.referrer)

if __name__ == '__main__':
    app.run()
