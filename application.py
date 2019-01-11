import os

from flask import Flask, session, render_template, redirect, request
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from helpers import login_required

app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Check for environment variable
if not os.getenv("DATABASE_URL"):
    raise RuntimeError("DATABASE_URL is not set")

# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine(os.getenv("DATABASE_URL"))
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():
    return "TO DO"


@app.route("/login", methods=['GET', 'POST'])
def login():

    session.clear()

    if request.method == "GET":

        return render_template("login.html")

    else:

        if not request.form.get("username"):
            return render_template("login.html", message = "Username Missing")
        if not request.form.get("password"):
            return render_template("login.html", message = "Password Missing")

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        if len(row) != 1 or row[0]["password"] != request.form.get("password"):
            return render_template("login.html", message = "Username or Password is Incorrect!")

        session["user_id"] = row[0]["user_id"]

        return redirect("/")

@app.route("/register", methods=['GET', 'POST'])
def register():

    session.clear()

    if request.method == "POST":

        if not request.form.get("firstname"):
            return render_template("register.html", message = "FirstName Missing")

        if not request.form.get("lastname"):
            return render_template("register.html", message="LastName Missing")

        if not request.form.get("username"):
            return render_template("register.html", message = "Username Missing")

        if not request.form.get("password"):
            return render_template("register.html", message="Password Missing")

        if request.form.get("password") !=  request.form.get("confirmation"):
            return render_template("register.html", message="Password do not match")

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        if len(row) != 0:
            return render_template("register.html", message = "Username Already Exist")

        else:
            key = db.execute("INSERT INTO users (firstname, lastname, username, password) VALUES(:firstname, :lastname, :username, :password)",
                  {'firstname': request.form.get("firstname"), 'lastname': request.form.get("lastname"), 'username': request.form.get("username"), 'password': request.form.get("password")})

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        session["user_id"] = row[0]["user_id"]

        db.commit()

        return redirect("/")

    else:

        return render_template("register.html")
