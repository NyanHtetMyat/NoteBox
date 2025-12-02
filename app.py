import os

from flask import Flask, flash, redirect, render_template, request, session, jsonify
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

    try:
        # Setup Database Connection
        db = get_db()

        # Query Note IDs and Titles only
        user_notes = db.execute("SELECT id, title FROM notes WHERE user_id = ? ORDER BY updated_at DESC", 
            (session["user_id"],)).fetchall()

    except Exception as e:
        return str(e), 403

    return render_template("index.html", user_notes=user_notes)


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


@app.route("/get_note_content")
@login_required
def get_note_content():
    """ To get user note contents """

    try:
        # Set up database connection
        db = get_db()

        # Get note id
        note_id = request.args.get("id").strip()

        # Check for missing ID
        if not note_id:
            raise Exception("Missing Note ID")

        # Get a single dict of Note Content and Last Updated Date ("user_id" is for checking Authentication)
        row_note_details = db.execute("SELECT title, content, updated_at FROM notes WHERE id = ? AND user_id = ?",
            (note_id, session["user_id"],)).fetchone()

        # Check if note exists
        if not row_note_details:
            raise Exception("Note Does not exist")

        # Change to actual Dict
        note_details = dict(row_note_details)

        return jsonify(note_details)
    
    except Exception as e:
        return str(e), 403


@app.route("/save_note", methods=["GET", "POST"])
@login_required
def save_note():
    """ To save a note """

    try:
        # Set up database connection
        db = get_db()

        # Get JSON string from JS
        note_details = request.get_json()

        # Check for empty JSON
        if not note_details:
            raise Exception("Empty JSON detected!")


        note_id = note_details.get("id", None)
        note_title = note_details.get("title", None)
        note_content = note_details.get("content", None)

        # Check for empty note
        if not (note_title or note_content):
            raise Exception("Empty note title or content detected!")

        # This block is for inserting new notes
        if not note_id:
            # Cursor is for reading meta data.
            cursor = db.execute("INSERT INTO notes (user_id, title, content) VALUES (?, ?, ?)",
                (session["user_id"], note_title, note_content,))

            db.commit()

            # Get New Note's title and Last Updated values
            new_note_details = db.execute("SELECT id, title, updated_at FROM notes WHERE id=?",
                (cursor.lastrowid,)).fetchone()

            # Change the result to actual dict and returns json string
            return jsonify(dict(new_note_details))
            

        # This block is for updating old notes
        else:
            db.execute("UPDATE notes SET title=?, content=? WHERE id=? AND user_id=?",
                (note_title, note_content, note_id, session["user_id"],))

            db.commit()

            # Get Edited Note's title and Last Updated values
            note_details = db.execute("SELECT id, title, updated_at FROM notes WHERE id = ?",
                (note_id,)).fetchone()

            return jsonify(dict(note_details))
    
    except Exception as e:
        db.rollback()
        return str(e), 403


@app.route("/del_note")
@login_required
def del_note():
    """ To delete a user note"""

    try:
        # Set up database connection
        db = get_db()

        # Get note id
        note_id = request.args.get("id").strip()

        # Check for missing ID
        if not note_id:
            raise Exception("Missing Note ID")

        # Delete row
        db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", 
            (note_id, session["user_id"]))

        db.commit()

    except Exception as e:
        db.rollback()
        return str(e), 403