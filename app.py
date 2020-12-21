from flask import Flask, render_template, request, session, redirect
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


#engine = create_engine('postgres://kbhpppsbtsabyk:6f9f47eb4721c77c17f1fccefeb2693a629e1f6e571bad88143561ba10e422be@ec2-52-20-248-222.compute-1.amazonaws.com:5432/d22l4qure274m')
#app.config["SESSION_PERMANENT"] = False
#app.config["SESSION_TYPE"] = "filesystem"
#Session(app)
#db = scoped_session(sessionmaker(bind=engine))
#ter system set idle_in_transaction_session_timeout='1min';
#SET SESSION idle_in_transaction_session_timeout = '1min';
#SQLALCHEMY_POOL_RECYCLE = 60
#alter database dbnamehere set statement_timeout = 600;

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

@app.route("/m/name/summary")
def m_summary():
    unrated = None
    while unrated == None:
        picked = random.choice(range(1000))
        unrated = db.execute("SELECT \"Michelle\" FROM \"name_list_g\" WHERE \"2020 Rank\" = :picked", {"picked": picked})

    name = db.execute("SELECT * FROM name_list_g WHERE \"2020 Rank\" = :picked", {"picked": picked})
    d, a = {}, []
    for rowproxy in name:
        for column, value in rowproxy.items():
            d = {**d, **{column: value}}
        a.append(d)
    name = a[0]['Name']
    rank = a[0]['2020 Rank']

    db.commit()

    return render_template("name_summary.html", unrated=unrated, name = name, rank=rank)

@app.route("/m/name/random")
def m_name_rand():
    unrated = None
    while unrated == None:
        picked = random.choice(range(1000))
        unrated = db.execute("SELECT \"Michelle\" FROM \"name_list_g\" WHERE \"2020 Rank\" = :picked", {"picked": picked})

    name = db.execute("SELECT * FROM name_list_g WHERE \"2020 Rank\" = :picked", {"picked": picked})
    d, a = {}, []
    for rowproxy in name:
        for column, value in rowproxy.items():
            d = {**d, **{column: value}}
        a.append(d)
    name = a[0]['Name']
    rank = a[0]['2020 Rank']

    db.commit()

    return render_template("name.html", unrated=unrated, name = name, rank=rank)

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        x = request.form['rating']
        y = request.form['name']
        db.execute("INSERT INTO name_log (\"rating\") VALUES (:x)", {"x": y})
        db.execute("UPDATE name_list_g SET \"Michelle\" = (:x) WHERE \"Name\" = (:y)", {"x": x, "y":y})
        db.commit()
        return redirect(request.referrer)

@app.route("/t/name/random")
def t_name_rand():
    unrated = None
    while unrated == None:
        picked = random.choice(range(1000))
        unrated = db.execute("SELECT \"Tommy\" FROM \"name_list_g\" WHERE \"2020 Rank\" = :picked", {"picked": picked})

    name = db.execute("SELECT * FROM name_list_g WHERE \"2020 Rank\" = :picked", {"picked": picked})
    d, a = {}, []
    for rowproxy in name:
        for column, value in rowproxy.items():
            d = {**d, **{column: value}}
        a.append(d)
    name = a[0]['Name']
    rank = a[0]['2020 Rank']

    db.commit()

    return render_template("name_t.html", unrated=unrated, name = name, rank=rank)

@app.route('/submit_t', methods=['POST'])
def submit_t():
    if request.method == 'POST':
        x = request.form['rating']
        y = request.form['name']
        db.execute("INSERT INTO name_log (\"rating\") VALUES (:x)", {"x": y})
        db.execute("UPDATE name_list_g SET \"Tommy\" = (:x) WHERE \"Name\" = (:y)", {"x": x, "y":y})
        db.commit()
        return redirect(request.referrer)

if __name__ == '__main__':
    app.run()
