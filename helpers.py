import requests

from flask import redirect, render_template, request, session
from functools import wraps


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def api(isbn):

    res = requests.get("https://www.goodreads.com/book/review_counts.json", params={"key": "kiJwHXKD8XFTv80gLRC3w", "isbns": isbn})
    if res.status_code != 200:
        return 404
    return res.json()

if __name__ == "__api__":
    api()
