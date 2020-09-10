from flask import Flask, render_template, request
#from flask_sqlalchemy import SQLAlchemy
from send_mail import send_mail
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

app = Flask(__name__)

ENV = 'dev'

if ENV == 'dev':
    app.debug = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://kbhpppsbtsabyk:6f9f47eb4721c77c17f1fccefeb2693a629e1f6e571bad88143561ba10e422be@ec2-52-20-248-222.compute-1.amazonaws.com:5432/d22l4qure274m'
else:
    app.debug = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgres://kbhpppsbtsabyk:6f9f47eb4721c77c17f1fccefeb2693a629e1f6e571bad88143561ba10e422be@ec2-52-20-248-222.compute-1.amazonaws.com:5432/d22l4qure274m'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

#db = SQLAlchemy(app)
engine = create_engine('postgres://kbhpppsbtsabyk:6f9f47eb4721c77c17f1fccefeb2693a629e1f6e571bad88143561ba10e422be@ec2-52-20-248-222.compute-1.amazonaws.com:5432/d22l4qure274m')
db = scoped_session(sessionmaker(bind=engine))

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
    return render_template('live.html')

@app.route('/leaderboard')
def leaderboard():
    return render_template('fpl_list.html')

@app.route('/submit', methods=['POST'])
def submit():
    if request.method == 'POST':
        customer = request.form['customer']
        dealer = request.form['dealer']
        rating = request.form['rating']
        comments = request.form['comments']
        # print(customer, dealer, rating, comments)
        if customer == '' or dealer == '':
            return render_template('index.html', message='Please enter required fields')
        if db.session.query(Feedback).filter(Feedback.customer == customer).count() == 0:
            data = Feedback(customer, dealer, rating, comments)
            db.session.add(data)
            db.session.commit()
            send_mail(customer, dealer, rating, comments)
            return render_template('success.html')
        return render_template('index.html', message='You have already submitted feedback')


if __name__ == '__main__':
    app.run()
