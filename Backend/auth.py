
from functools import wraps

from flask import Blueprint, jsonify, session
from extensions import db
from models import User

auth_bp = Blueprint("auth", __name__)


def get_current_user():
    """Return the logged-in user, or None."""
    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def login_required(view):
    """Protect a route so only logged-in users can access it."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if get_current_user() is None:
            return jsonify({"error": "Please log in first."}), 401

        return view(*args, **kwargs)

    return wrapped_view
