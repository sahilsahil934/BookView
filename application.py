import os

from flask import Flask, session, render_template, redirect, request, url_for, flash, jsonify
from flask_session import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date


from helpers import login_required, api_data

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


# Configure session to use filesystem
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Set up database
engine = create_engine("postgres://postgres:12345@localhost:5432/books")
db = scoped_session(sessionmaker(bind=engine))


@app.route("/")
@login_required
def index():

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()
    posts = db.execute("SELECT * from posts ORDER BY post_id DESC").fetchall()
    if len(user) != 0:

        return render_template("index.html", user = user, posts=posts)

    else:
        return redirect("/login")


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

        if len(row) != 1 or not check_password_hash(row[0]["password"], request.form.get("password")):
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
                  {'firstname': request.form.get("firstname"), 'lastname': request.form.get("lastname"), 'username': request.form.get("username").lower(),
                   'password': generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)})
        

        row = db.execute("SELECT * FROM users WHERE username = :username", {'username': request.form.get("username")}).fetchall()

        x = row[0]["user_id"]
        db.execute("INSERT INTO profile (user_id) VALUES(:user)",{'user':int(x)})
        db.execute("INSERT INTO social (user_id) VALUES(:user)",{'user':int(x)})

        session["user_id"] = row[0]["user_id"]

        db.commit()

        return redirect("/")

    else:

        return render_template("register.html")

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():

    if request.method == "GET":

        return redirect("/")

    else:

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        if not request.form.get("search"):
            return redirect("/")

        rows = db.execute("SELECT DISTINCT isbn, title, author FROM books WHERE LOWER(isbn) LIKE :search OR LOWER(title) LIKE :search OR LOWER(author) LIKE :search", {'search': '%' + request.form.get("search").lower() + '%'}).fetchall()

        if rows != 0:
            return render_template("search.html", rows=rows, search=request.form.get("search"), user=user)
        else:
            return render_template("search.html", search=request.form.get("search"), user=user)



@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "GET":

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        profile = db.execute("SELECT * FROM profile WHERE user_id = :user", {'user': int(session['user_id'])}).fetchall()
        social = db.execute("SELECT * FROM social WHERE user_id = :user", {'user': int(session['user_id'])}).fetchall()
        return render_template("profile.html", user=user, profile=profile, social=social)

@app.route("/social", methods=["GET", "POST"])
@login_required
def social():

    if request.method == "GET":

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        social = db.execute("SELECT * FROM social WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()
        return render_template("social.html", user=user,social=social)

    else:

        rows = db.execute("SELECT * FROM users WHERE user_id = :user_id", {'user_id':session["user_id"]}).fetchall()

        db.execute("UPDATE social SET web = :web, twitter = :twitter, instagram = :instagram, fb = :fb WHERE user_id = :user_id",
                       {'user_id':session["user_id"],
                       'web': request.form.get("web"), 'twitter': request.form.get("twitter"), 'instagram': request.form.get("instagram"), 'fb': request.form.get("fb")})

        db.commit()
        flash("Social updated")
        return redirect(url_for('profile'))


@app.route("/book/<title>", methods=["GET", "POST"])
@login_required
def book(title):

    if request.method == "GET":

        rating = 404
        
        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        rows = db.execute("SELECT * FROM books WHERE title = :title", {'title': title}).fetchall() 

        if len(rows) != 0:
            rating = api_data(rows[0]["isbn"])

        fav = db.execute("SELECT * FROM fav WHERE user_id = :user_id AND book_id = :book_id", {'user_id': int(session["user_id"]), 'book_id': rows[0]["id"]}).fetchall()


        rate = db.execute("SELECT firstname, review, rating FROM review JOIN users ON review.user_id = users.user_id WHERE book_id = :id", {'id': rows[0]["id"]}).fetchall()

        if len(fav) != 0:
            if rating == 404:
                return render_template("book.html", rows = rows, user=user, rate=rate, message="Remove from Favourite")

            return render_template("book.html", rows = rows, user=user, rate=rate, rating=rating, message="Remove from Favourite")

        else:
            if rating == 404:
                return render_template("book.html", rows = rows, user=user, rate=rate, message="Add to Favourite")

            return render_template("book.html", rows = rows, user=user, rate=rate, rating=rating, message="Add to Favourite")

    else:

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        rows = db.execute("SELECT * FROM books WHERE title = :title", {'title': title}).fetchall()

        rate = db.execute("SELECT * FROM review WHERE user_id = :id AND book_id = :book_id", {'id': session["user_id"], 'book_id': rows[0]["id"]}).fetchall()

        if not request.form.get("rating"):
            return render_template("error.html", message = "Must provide rating", user=user)

        if len(rate) != 0:
            return render_template("already.html", user=user, rate=rate, rows=rows)

        if not request.form.get("comment"):


            db.execute("INSERT INTO review (user_id, book_id, rating) VALUES(:user_id, :book_id, :rating)", {'user_id': int(session["user_id"]), 'book_id': rows[0]["id"], 'rating': int(request.form.get("rating"))})
        else:

            db.execute("INSERT INTO review (user_id, book_id, review, rating) VALUES(:user_id, :book_id, :review, :rating)", {'user_id': int(session["user_id"]), 'book_id': rows[0]["id"], 'review': request.form.get("comment"), 'rating': int(request.form.get("rating"))})

        db.commit()

        return redirect(url_for('book', title=rows[0]["title"]))

@app.route("/delete/<id>")
@login_required
def delete(id):

    db.execute("DELETE FROM review WHERE user_id = :id AND book_id = :book_id", {'id': int(session["user_id"]), 'book_id': int(id)})
    db.commit()

    rows = db.execute("SELECT * FROM books WHERE id = :id", {'id': id}).fetchall()

    return redirect(url_for('book', title=rows[0]["title"]))

@app.route("/password", methods=["GET", "POST"])
@login_required
def password():

    user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

    if request.method == "GET":

        return render_template("password.html", user=user)

    else:

        if not request.form.get("old"):
            return render_template("password.html", message="Missing Old Password", user=user)

        elif not request.form.get("password"):
            return render_template("password.html", message="Missing new password", user=user)

        elif request.form.get("confirmation") != request.form.get("password"):
            return render_template("password.html", message="Password don't Match", user=user)

        rows = db.execute("SELECT * FROM users WHERE user_id = :user_id", {'user_id':session["user_id"]}).fetchall()

        if not check_password_hash(rows[0]["password"], request.form.get("old")):
            return render_template("password.html", message="Wrong old Password", user=user)

        else:
            db.execute("UPDATE users SET password = :hash WHERE user_id = :user_id",
                       {'user_id':session["user_id"],
                       'hash':generate_password_hash(request.form.get("password"), method='pbkdf2:sha256', salt_length=8)})

            db.commit()
        flash("Password Changed")
        return redirect(url_for('index'))

@app.route("/fav/<id>", methods=["GET", "POST"])
@login_required
def fav(id):

    if request.method == "GET":

        rows = db.execute("SELECT isbn, title, Author FROM books JOIN fav ON books.id = fav.book_id WHERE user_id = :user_id", {'user_id': session["user_id"]}).fetchall()

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        return render_template("fav.html", user=user, rows=rows, search="Favourite")

    else:

        book = db.execute("SELECT * FROM fav WHERE user_id = :user_id AND book_id = :book_id", {'user_id': session["user_id"], 'book_id': id}).fetchall()

        if len(book) == 0:

            db.execute("INSERT INTO fav (user_id, book_id) VALUES(:user_id, :book_id)", {'user_id': session["user_id"], 'book_id': id })
            db.commit()
            flash("Added to favourite")

        else:

            db.execute("DELETE FROM fav WHERE user_id = :user_id AND book_id = :book_id", {'user_id': session["user_id"], 'book_id': id})
            db.commit()
            flash("Deleted from Favourite")

        return redirect(url_for('fav', id=id))

@app.route("/api/<isbn>")
def api(isbn):

    detail = db.execute("SELECT * FROM books WHERE isbn = :isbn", {'isbn': isbn}).fetchall()

    if len(detail) == 0:
        return jsonify({"error": "Invalid ISBN"}, 404)

    book = db.execute("SELECT * FROM review WHERE book_id = :book_id", {'book_id': detail[0]["id"]}).fetchall()

    total = len(book)
    sum = 0

    for i in book:
        sum += i["rating"]

    average = sum/total

    return jsonify({
                    "title": detail[0]["title"],
                    "author": detail[0]["author"],
                    "year": detail[0]["year"],
                    "isbn": isbn,
                    "review_count": total,
                    "average_score": average
                    })


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():

    if request.method == "GET":

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()

        profile = db.execute("SELECT * FROM profile WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()
        return render_template("edit_profile.html", user=user, profile=profile)

    else:

        rows = db.execute("SELECT * FROM users WHERE user_id = :user_id", {'user_id':session["user_id"]}).fetchall()

        db.execute("UPDATE profile SET age = :age,  sex = :sex, occ = :occ, email = :email, mobile = :mobile, country = :country, genre = :genre, interests = :interests, books = :books, movies = :movies, quote = :quote WHERE user_id = :user_id",
                       {'user_id':session["user_id"],
                       'age': request.form.get("age"), 'sex': request.form.get("sex"), 'occ': request.form.get("occ"), 'email': request.form.get("email"), 'mobile': request.form.get("mobile"), 'country': request.form.get("country"), 'genre': request.form.get("genre"), 'interests': request.form.get("interests"), 'books': request.form.get("books"), 'movies': request.form.get("movies"), 'quote': request.form.get("quote")})

        db.commit()
        flash("Social updated")
        return redirect(url_for('profile'))

@app.route("/post", methods=["GET", "POST"])
@login_required
def post():

    if request.method == "POST":

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': int(session["user_id"])}).fetchall()
        if not request.form.get("post"):
            return render_template("index.html", message = "Post Missing")
        
        today_date = date.today()
        db.execute("INSERT INTO posts (user_id, name, deatil, date) VALUES (:user, :name, :detail, :date)", {'user': int(session["user_id"]), 'name': user[0]["firstname"] + user[0]["lastname"], 'detail': request.form.get("post"), 'date': today_date})
        db.commit()
        return redirect("/")
       
@app.route("/showprofile/<id>", methods=["GET", "POST"])
@login_required
def showprofile(id):

    if request.method == "GET":

        user = db.execute("SELECT * FROM users WHERE user_id = :user", {'user': id}).fetchall()
        print(id)
        profile = db.execute("SELECT * FROM profile WHERE user_id = :user", {'user': id}).fetchall()
        social = db.execute("SELECT * FROM social WHERE user_id = :user", {'user': id}).fetchall()
        return render_template("showprofile.html", user=user, profile=profile, social=social)