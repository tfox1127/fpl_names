from flask import Flask, render_template, request
#from flask_sqlalchemy import SQLAlchemy
from send_mail import send_mail
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

ENV = 'dev'

engine = create_engine('postgres://kbhpppsbtsabyk:6f9f47eb4721c77c17f1fccefeb2693a629e1f6e571bad88143561ba10e422be@ec2-52-20-248-222.compute-1.amazonaws.com:5432/d22l4qure274m')
db = scoped_session(sessionmaker(bind=engine))
SQLALCHEMY_POOL_RECYCLE = 60

@app.route('/')
def index():
    elements = db.execute("SELECT * FROM blog ORDER BY post_number DESC LIMIT 10").fetchall()
    return render_template('index.html', elements=elements)

@app.route('/lms')
def lms():
    return render_template('lms.html')

@app.route('/lcs')
def lcs():
    return render_template('lcs.html')

@app.route('/cups')
def cups():
    return render_template('cups.html')

@app.route('/live')
def live():
    elements = db.execute('SELECT * FROM live').fetchall()
    return render_template('live.html', elements=elements)

@app.route('/leaderboard')
def leaderboard():
    return render_template('fpl_list.html')

@app.route('/hof')
def hof():
    elements = db.execute('SELECT * FROM hof').fetchall()
    return render_template('hof.html', elements=elements)


if __name__ == '__main__':
    app.run()
