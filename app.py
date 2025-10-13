import os

from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from flask import g
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import login_required, admin_only

import sqlite3

# Configure application
app = Flask(__name__)


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure Database
DATABASE = "database.db"


def get_db():
    """ To setup Database connection object """
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row

    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """ Close db connection after every request """
    db = g.pop("db", None)

    if db:
        db.close()


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """ User Dashboard """
    return render_template("index.html")


@app.route("/admin")
@login_required
@admin_only
def admin():
    """ Admin Dashboard """
    return render_template("admin.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """ Login for user or admin """

    session.clear()

    if request.method == "POST":

        try:
            # Setup Database connection
            db = get_db()

            username = request.form.get("username").strip()
            password = request.form.get("password").strip()

            # Checks for empty fields
            if not (username and password):
                raise Exception("Invalid username or password")

            # Get the user
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchall()

            # Check for user existance and correct password
            if not (user and check_password_hash(user[0]["password_hash"], password)):
                raise Exception("Invalid username or password")

            # Add user details to the session
            session["user_id"] = user[0]["id"]
            session["user_name"] = user[0]["username"]
            session["user_role"] = user[0]["role"]

            # Redirect to either user or admin dashboard
            if user[0]["role"] == "admin":
                return redirect("/admin")
            else:
                return redirect("/")
        
        except Exception as e:
            return str(e), 403

    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/login")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    session.clear()

    if request.method == "POST":
        try:

            # Setup Database connection
            db = get_db()

            username = request.form.get("username")
            password = request.form.get("password")
            cpassword = request.form.get("cpassword")

            # Check for empty fields
            if not (username.strip() and password.strip() and cpassword.strip()):
                raise Exception("Missing fields!")

            # Check for password confirmation
            if password != cpassword:
                raise Exception("Passwords do not match!")

            # Check for existing user
            result = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchall()

            if len(result) >= 1:
                raise Exception("Username already exists!")

            # Create User Account
            db.execute("INSERT INTO users (username, password_hash) VALUES(?, ?)",
                (username, generate_password_hash(password),))

            db.commit()

            # Assign user details to session
            user = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchall()
            
            session["user_id"] = user[0]["id"]
            session["user_name"] = user[0]["username"]
            session["user_role"] = user[0]["role"]

            # Redirects to user dashboard
            return redirect("/")

        except Exception as e:
            return str(e), 403

    else:
        return render_template("register.html")


@app.route("/test")
def test():
    return render_template("test.html")