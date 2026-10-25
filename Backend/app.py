
import os
from pathlib import Path




from dotenv import load_dotenv
from flask import Flask, jsonify, request, session
from extensions import db
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(__name__)

app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY")
if not app.config["SECRET_KEY"]:
    raise RuntimeError("FLASK_SECRET_KEY is missing from Backend/.env")

database_url = os.environ.get("DATABASE_URL")

if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    database_url or ("sqlite:///" + str(BASE_DIR / "trustvault.db"))
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True

is_production = os.environ.get("FLASK_ENV") == "production"
app.config["SESSION_COOKIE_SECURE"] = is_production
app.config["SESSION_COOKIE_SAMESITE"] = (
    "None" if is_production else "Lax"
)

frontend_origins = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_URL", "http://localhost:5173,http://localhost:5174"
    ).split(",")
    if origin.strip()
]

CORS(
    app,
    origins=frontend_origins,
    supports_credentials=True,
)
db.init_app(app)

# Import models after db is initialized.
from models import User
from documents import documents_bp
app.register_blueprint(documents_bp)

with app.app_context():
    db.create_all()

@app.route("/")
def home():

    return jsonify({
        "project": "TrustVault",
        "message": "Secure Document Sharing API is running",
        "status": "success",
    })


@app.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not name or not email or not isinstance(password, str):
        return jsonify({"error": "Name, email, and password are required."}), 400

    if len(name) > 100 or len(email) > 255 or len(password) < 8:
        return jsonify({
            "error": "Name/email is too long or password is shorter than 8 characters."
        }), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "An account with this email already exists."}), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
    )
    db.session.add(user)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id

    return jsonify({
        "message": "Registration successful.",
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }), 201


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    password = data.get("password", "")

    if not email or not isinstance(password, str) or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session["user_id"] = user.id

    return jsonify({
        "message": "Login successful.",
        "user": {"id": user.id, "name": user.name, "email": user.email},
    })


@app.route("/api/me")
def current_user():
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Please log in."}), 401

    user = db.session.get(User, user_id)
    if not user:
        session.clear()
        return jsonify({"error": "Please log in again."}), 401

    return jsonify({
        "user": {"id": user.id, "name": user.name, "email": user.email}
    })


@app.route("/api/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."})


if __name__ == "__main__":
    app.run(debug=True)
