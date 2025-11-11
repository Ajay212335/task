import os
import uuid
import json
import sqlite3
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from functools import wraps

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import requests
from dotenv import load_dotenv
import jwt
from pymongo import MongoClient
from flask_cors import CORS
from datetime import datetime, timedelta
# ------------------------------------------------------------
# Load Environment Variables
# ------------------------------------------------------------
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-change-me")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE = os.getenv("OPENROUTER_BASE", "https://openrouter.ai/api/v1")
OTP_EXPIRE_MIN = int(os.getenv("OTP_EXPIRE_MIN", "5"))
PORT = int(os.getenv("PORT", 5000))

# ------------------------------------------------------------
# Flask App Setup
# ------------------------------------------------------------
app = Flask(__name__, static_folder="frontend/dist", static_url_path="/")
CORS(app, resources={r"/api/*": {"origins": "*"}})

# ------------------------------------------------------------
# MongoDB Connection
# ------------------------------------------------------------
try:
    client = MongoClient(MONGO_URI)
    db_name = MONGO_URI.split("/")[-1].split("?")[0] or "ecommerce"
    mongo_db = client[db_name]
    print(f"✅ Connected to MongoDB database: {db_name}")
except Exception as e:
    print("❌ Failed to connect to MongoDB:", e)
    mongo_db = None

# ------------------------------------------------------------
# SQLite Backup Database
# ------------------------------------------------------------
SQLITE_FILE = "backup_users.db"
conn = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS users_backup (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    email TEXT UNIQUE,
    password_hash TEXT,
    created_at TEXT
)
""")
conn.commit()

# In-memory OTP store
otp_store = {}

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------
def send_otp_via_email(email, otp):
    """Send OTP to user's email."""
    if not EMAIL_USER or not EMAIL_PASS:
        print(f"[DEV MODE] OTP for {email}: {otp}")
        return

    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    msg["To"] = email
    msg["Subject"] = "Your OTP Code - Verification"
    body = f"""
    Hello 👋,

    Your OTP code is: {otp}

    This code is valid for {OTP_EXPIRE_MIN} minutes.

    Thank you,
    ChatBot Support Team
    """
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
        print(f"✅ OTP sent successfully to {email}")
    except Exception as e:
        print(f"❌ Failed to send OTP to {email}: {e}")


def auth_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            auth = request.headers.get("Authorization")
            if auth.startswith("Bearer "):
                token = auth.split(" ", 1)[1]
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            request.user = payload
        except Exception as e:
            return jsonify({"error": "Invalid token", "details": str(e)}), 401
        return f(*args, **kwargs)
    return wrapper


def call_openrouter_prompt(messages, max_tokens=256):
    """Call OpenRouter API for chatbot."""
    if not OPENROUTER_API_KEY:
        return {"error": "No OpenRouter API key configured"}

    url = f"{OPENROUTER_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": os.getenv("OPENROUTER_MODEL", "gpt-4o-mini"),
        "messages": messages,
        "max_tokens": max_tokens,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            return {"error": f"OpenRouter error: {resp.status_code}", "details": resp.text}
        return resp.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return {"error": str(e)}

# ------------------------------------------------------------
# Product Seeder
# ------------------------------------------------------------
def seed_products():
    if mongo_db is None:
        print("❌ MongoDB not connected, skipping seed.")
        return

    products = [
        {"product_id": "p1", "name": "Running Shoes", "price": 49.99, "stock": 10},
        {"product_id": "p2", "name": "Wireless Headphones", "price": 69.99, "stock": 8},
        {"product_id": "p3", "name": "Smart Watch", "price": 129.99, "stock": 5},
        {"product_id": "p4", "name": "Backpack", "price": 39.99, "stock": 12},
        {"product_id": "p5", "name": "Sunglasses", "price": 19.99, "stock": 20},
    ]

    try:
        if mongo_db["products"].count_documents({}) == 0:
            mongo_db["products"].insert_many(products)
            print("✅ Products seeded successfully in MongoDB")
        else:
            print("ℹ️ Products already exist, skipping seed")
    except Exception as e:
        print("❌ Failed to seed products:", e)

seed_products()

# ------------------------------------------------------------
# Register with Email OTP
# ------------------------------------------------------------
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm = data.get("confirm", "")

    if not (name and email and password and confirm):
        return jsonify({"error": "All fields are required"}), 400
    if password != confirm:
        return jsonify({"error": "Passwords do not match"}), 400

    users_col = mongo_db["users"]
    if users_col.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 400

    otp = str(uuid.uuid4().int)[:6]
    expires = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MIN)
    token = str(uuid.uuid4())

    otp_store[token] = {
        "email": email,
        "name": name,
        "password_hash": generate_password_hash(password),
        "otp": otp,
        "expires_at": expires,
    }

    send_otp_via_email(email, otp)
    return jsonify({"message": "OTP sent successfully", "otp_token": token})

# ------------------------------------------------------------
# Verify OTP
# ------------------------------------------------------------
@app.route("/api/verify_otp", methods=["POST"])
def verify_otp():
    data = request.json or {}
    token = data.get("otp_token")
    otp = data.get("otp")

    entry = otp_store.get(token)
    if not entry:
        return jsonify({"error": "Invalid or expired token"}), 400
    if datetime.now(timezone.utc) > entry["expires_at"]:
        otp_store.pop(token, None)
        return jsonify({"error": "OTP expired"}), 400
    if entry["otp"] != otp:
        return jsonify({"error": "Incorrect OTP"}), 400

    users_col = mongo_db["users"]
    user_id = str(uuid.uuid4())
    user_doc = {
        "user_id": user_id,
        "name": entry["name"],
        "email": entry["email"],
        "password_hash": entry["password_hash"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    users_col.insert_one(user_doc)

    cur.execute(
        "INSERT OR REPLACE INTO users_backup (user_id, name, email, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, entry["name"], entry["email"], entry["password_hash"], datetime.now(timezone.utc).isoformat()),
    )
    conn.commit()
    otp_store.pop(token, None)
    return jsonify({"message": "OTP verified successfully, registration complete"})

# ------------------------------------------------------------
# Login
# ------------------------------------------------------------
@app.route("/api/login", methods=["POST"])
def login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = mongo_db["users"].find_one({"email": email})
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    payload = {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user["name"],
        "exp": datetime.now(timezone.utc) + timedelta(hours=12),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    return jsonify({"token": token})

# ------------------------------------------------------------
# Products
# ------------------------------------------------------------
@app.route("/api/products", methods=["GET"])
def get_products():
    products = list(mongo_db["products"].find({}, {"_id": 0}))
    return jsonify(products)

@app.route("/api/order", methods=["POST"])
@auth_required
def create_order():
    data = request.json or {}
    product_id = data.get("product_id")
    qty = int(data.get("quantity", 1))

    prod = mongo_db["products"].find_one({"product_id": product_id})
    if not prod:
        return jsonify({"error": "Product not found"}), 404
    if prod.get("stock", 0) < qty:
        return jsonify({"error": "Not enough stock"}), 400

    order_id = str(uuid.uuid4().hex)[:12]
    order = {
        "order_id": order_id,
        "user_id": request.user["user_id"],
        "items": [{"product_id": product_id, "qty": qty, "price": prod["price"]}],
        "status": "processing",
        "created_at": datetime.utcnow().isoformat(),
    }

    mongo_db["orders"].insert_one(order)
    mongo_db["products"].update_one({"product_id": product_id}, {"$inc": {"stock": -qty}})
    return jsonify({"message": "Order placed successfully", "order_id": order_id})

@app.route("/api/order/<order_id>", methods=["GET"])
@auth_required
def get_order(order_id):
    o = mongo_db["orders"].find_one({"order_id": order_id}, {"_id": 0})
    if not o:
        return jsonify({"error": "Order not found"}), 404
    if o["user_id"] != request.user["user_id"]:
        return jsonify({"error": "Not authorized"}), 403
    return jsonify(o)

# ------------------------------------------------------------
# Chatbot (RAG + LLM)
# ------------------------------------------------------------
@app.route("/api/chat", methods=["POST"])
@auth_required
def chat():
    data = request.json or {}
    text = data.get("message", "").strip().lower()
    order_id = data.get("order_id")  # optional: user can provide order_id directly

    # ----------------------
    # Check if the user input looks like an order number
    # ----------------------
    if not order_id:
        # If message is only digits (or alphanumeric, like order_id hex), treat it as order_id
        if text.isdigit() or (len(text) >= 8 and all(c.isalnum() for c in text)):
            order_id = text

    # ----------------------
    # Order status query
    # ----------------------
    if order_id:
        o = mongo_db["orders"].find_one({"order_id": order_id})
        if o and o["user_id"] == request.user["user_id"]:
            try:
                order_date = datetime.fromisoformat(o['created_at'])
            except:
                order_date = datetime.utcnow()
            estimated_delivery = order_date + timedelta(days=5)
            estimated_str = estimated_delivery.strftime("%d %b %Y")
            return jsonify({
                "bot": f"Your order #{order_id} is {o['status']} (placed on {order_date.strftime('%d %b %Y')}). "
                       f"Estimated delivery: {estimated_str}."
            })
        else:
            # Order not found or doesn't belong to the user
            return jsonify({
                "bot": "I don’t have access to that information, but I can forward your request to our support team. Would you like me to do that?"
            })

    # ----------------------
    # Returns query
    # ----------------------
    if "return" in text or "how do i return" in text:
        return jsonify({
            "bot": "I don’t have access to that information, but I can forward your request to our support team. Would you like me to do that?"
        })

    # ----------------------
    # Change shipping address query
    # ----------------------
    if "change shipping address" in text or "update address" in text:
        return jsonify({
            "bot": "I don’t have access to that information, but I can forward your request to our support team. Would you like me to do that?"
        })

    # ----------------------
    # Any other query
    # ----------------------
    return jsonify({
        "bot": "I don’t have access to that information, but I can forward your request to our support team. Would you like me to do that?"
    })


# ------------------------------------------------------------
# Profile & History
# ------------------------------------------------------------
@app.route("/api/profile", methods=["GET"])
@auth_required
def profile():
    u = mongo_db["users"].find_one({"user_id": request.user["user_id"]}, {"_id": 0, "password_hash": 0})
    if not u:
        return jsonify({"error": "User not found"}), 404
    orders = list(mongo_db["orders"].find({"user_id": request.user["user_id"]}, {"_id": 0}))
    return jsonify({"profile": u, "orders": orders})

# ------------------------------------------------------------
# Serve Frontend
# ------------------------------------------------------------
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

# ------------------------------------------------------------
# Run Server
# ------------------------------------------------------------
if __name__ == "__main__":
    seed_products()
    app.run(debug=True, port=PORT)
