import requests

from flask import redirect, render_template, session
from functools import wraps


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")

        return func(*args, **kwargs)

    return wrapper


def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("user_role", None) != "admin":
            return redirect("/login")

        return func(*args, **kwargs)

    return wrapper