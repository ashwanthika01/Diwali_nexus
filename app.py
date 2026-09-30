import os, sqlite3, secrets
from functools import wraps
from datetime import date
from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from werkzeug.security import generate_password_hash, check_password_hash

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("DATABASE_PATH", os.path.join(APP_DIR, "diwali_fund.db"))
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-this-secret-before-deploying")

DEFAULT_PLANS = [
    ("Classic", 5000, 500, 10, "Sample plan; terms must be legally reviewed."),
    ("Silver", 10000, 1000, 10, "Sample plan; terms must be legally reviewed."),
    ("Gold", 25000, 2500, 10, "Sample plan; terms must be legally reviewed."),
    ("Premium", 50000, 5000, 10, "Sample plan; terms must be legally reviewed."),
]

def db_conn():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      mobile TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      role TEXT NOT NULL DEFAULT 'customer',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS plans(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      total_amount INTEGER NOT NULL CHECK(total_amount > 0),
      monthly_amount INTEGER NOT NULL CHECK(monthly_amount > 0),
      duration_months INTEGER NOT NULL CHECK(duration_months > 0),
      terms TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS memberships(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL REFERENCES users(id),
      plan_id INTEGER NOT NULL REFERENCES plans(id),
      status TEXT NOT NULL DEFAULT 'pending',
      joined_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS collections(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      membership_id INTEGER NOT NULL REFERENCES memberships(id),
      due_month TEXT NOT NULL,
      amount INTEGER NOT NULL CHECK(amount > 0),
      status TEXT NOT NULL DEFAULT 'pending',
      paid_at TEXT,
      reference TEXT DEFAULT '',
      UNIQUE(membership_id, due_month)
    );
    """)
    count = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
    if count == 0:
        conn.executemany("INSERT INTO plans(name,total_amount,monthly_amount,duration_months,terms) VALUES(?,?,?,?,?)", DEFAULT_PLANS)
    conn.commit()
    conn.close()

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db_conn().execute("SELECT id,name,mobile,role FROM users WHERE id=?", (uid,)).fetchone()

@app.context_processor
def inject_user():
    return {"current_user": current_user(), "today": date.today().isoformat()}

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user():
            flash("முதலில் login செய்யுங்கள்.", "warning")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        u = current_user()
        if not u or u["role"] != "admin":
            flash("இந்தப் பக்கம் admin-க்கு மட்டும்.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    plans = db_conn().execute("SELECT * FROM plans WHERE active=1 ORDER BY total_amount").fetchall()
    return render_template("index.html", plans=plans)

@app.route("/register", methods=["GET", "POST"])
def register():
    plans = db_conn().execute("SELECT * FROM plans WHERE active=1 ORDER BY total_amount").fetchall()
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        plan_id = request.form.get("plan_id", type=int)
        if not name or not mobile.isdigit() or len(mobile) != 10 or len(password) < 8:
            flash("பெயர், 10 இலக்க mobile number, குறைந்தது 8 எழுத்து password கொடுக்கவும்.", "error")
            return render_template("register.html", plans=plans)
        conn = db_conn()
        try:
            cur = conn.execute("INSERT INTO users(name,mobile,password_hash) VALUES(?,?,?)",
                               (name, mobile, generate_password_hash(password)))
            uid = cur.lastrowid
            if plan_id and conn.execute("SELECT id FROM plans WHERE id=? AND active=1", (plan_id,)).fetchone():
                mcur = conn.execute("INSERT INTO memberships(user_id,plan_id,status) VALUES(?,?,?)", (uid, plan_id, "pending_review"))
                plan = conn.execute("SELECT * FROM plans WHERE id=?", (plan_id,)).fetchone()
                # Create future monthly due rows only as a schedule; no payment is implied.
                from datetime import date
                y, mo = date.today().year, date.today().month
                for i in range(plan["duration_months"]):
                    mm = mo + i
                    yy = y + (mm - 1)//12
                    mm = (mm - 1)%12 + 1
                    conn.execute("INSERT OR IGNORE INTO collections(membership_id,due_month,amount) VALUES(?,?,?)",
                                 (mcur.lastrowid, f"{yy:04d}-{mm:02d}", plan["monthly_amount"]))
            conn.commit()
            session["user_id"] = uid
            flash("Account உருவாக்கப்பட்டது. Membership admin review-க்காக pending-ல் உள்ளது.", "success")
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash("இந்த mobile number ஏற்கனவே பதிவு செய்யப்பட்டுள்ளது.", "error")
    return render_template("register.html", plans=plans)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        mobile = request.form.get("mobile", "").strip()
        password = request.form.get("password", "")
        user = db_conn().execute("SELECT * FROM users WHERE mobile=?", (mobile,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash("Login successful.", "success")
            return redirect(url_for("admin_dashboard" if user["role"] == "admin" else "dashboard"))
        flash("Mobile number அல்லது password சரியில்லை.", "error")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Logout செய்யப்பட்டுவிட்டது.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    u = current_user()
    conn = db_conn()
    memberships = conn.execute("""SELECT m.*,p.name AS plan_name,p.total_amount,p.monthly_amount,p.duration_months
      FROM memberships m JOIN plans p ON p.id=m.plan_id WHERE m.user_id=? ORDER BY m.id DESC""", (u["id"],)).fetchall()
    rows = conn.execute("""SELECT c.*,p.name AS plan_name FROM collections c
      JOIN memberships m ON m.id=c.membership_id JOIN plans p ON p.id=m.plan_id
      WHERE m.user_id=? ORDER BY c.due_month DESC""", (u["id"],)).fetchall()
    return render_template("dashboard.html", memberships=memberships, collections=rows)

@app.route("/admin")
@admin_required
def admin_dashboard():
    conn = db_conn()
    users = conn.execute("SELECT id,name,mobile,role,created_at FROM users ORDER BY id DESC").fetchall()
    plans = conn.execute("SELECT * FROM plans ORDER BY id").fetchall()
    memberships = conn.execute("""SELECT m.*,u.name AS customer_name,u.mobile,p.name AS plan_name,p.monthly_amount
      FROM memberships m JOIN users u ON u.id=m.user_id JOIN plans p ON p.id=m.plan_id ORDER BY m.id DESC""").fetchall()
    collections = conn.execute("""SELECT c.*,u.name AS customer_name,u.mobile,p.name AS plan_name
      FROM collections c JOIN memberships m ON m.id=c.membership_id JOIN users u ON u.id=m.user_id
      JOIN plans p ON p.id=m.plan_id ORDER BY c.due_month DESC,u.name""").fetchall()
    totals = {
      "customers": conn.execute("SELECT COUNT(*) FROM users WHERE role='customer'").fetchone()[0],
      "memberships": conn.execute("SELECT COUNT(*) FROM memberships").fetchone()[0],
      "pending": conn.execute("SELECT COUNT(*) FROM collections WHERE status='pending'").fetchone()[0],
      "paid": conn.execute("SELECT COALESCE(SUM(amount),0) FROM collections WHERE status='paid'").fetchone()[0],
    }
    return render_template("admin.html", users=users, plans=plans, memberships=memberships, collections=collections, totals=totals)

@app.route("/admin/plan", methods=["POST"])
@admin_required
def add_plan():
    name = request.form.get("name", "").strip()
    total = request.form.get("total_amount", type=int)
    monthly = request.form.get("monthly_amount", type=int)
    duration = request.form.get("duration_months", type=int)
    terms = request.form.get("terms", "").strip()
    if not name or not total or not monthly or not duration or min(total, monthly, duration) <= 0:
        flash("Plan விவரங்களை சரியாக நிரப்பவும்.", "error")
    else:
        db_conn().execute("INSERT INTO plans(name,total_amount,monthly_amount,duration_months,terms) VALUES(?,?,?,?,?)",
                          (name,total,monthly,duration,terms))
        db_conn().commit()
        flash("Plan சேர்க்கப்பட்டது. இது இன்னும் legal review செய்யப்பட்ட plan என்று பொருளல்ல.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/plan/<int:plan_id>/toggle", methods=["POST"])
@admin_required
def toggle_plan(plan_id):
    conn = db_conn()
    conn.execute("UPDATE plans SET active=CASE active WHEN 1 THEN 0 ELSE 1 END WHERE id=?", (plan_id,))
    conn.commit()
    flash("Plan status மாற்றப்பட்டது.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/membership/<int:mid>/approve", methods=["POST"])
@admin_required
def approve_membership(mid):
    conn = db_conn()
    conn.execute("UPDATE memberships SET status='active' WHERE id=?", (mid,))
    conn.commit()
    flash("Membership status active என மாற்றப்பட்டது. தேவையான சட்ட அனுமதிகள் தனியாக உறுதி செய்யப்பட வேண்டும்.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/collection/<int:cid>/paid", methods=["POST"])
@admin_required
def mark_paid(cid):
    ref = request.form.get("reference", "").strip()
    conn = db_conn()
    conn.execute("UPDATE collections SET status='paid',paid_at=CURRENT_TIMESTAMP,reference=? WHERE id=?", (ref,cid))
    conn.commit()
    flash("Demo/manual collection entry update செய்யப்பட்டது. Bank/payment gateway-ல் உண்மையான settlement நடந்ததா தனியாக சரிபார்க்கவும்.", "warning")
    return redirect(url_for("admin_dashboard"))

@app.route("/health")
def health():
    return {"status":"ok","app":"VIP NEXUS Diwali Fund prototype"}

if __name__ == "__main__":
    init_db()
    print("First-run admin setup: set ADMIN_MOBILE and ADMIN_PASSWORD before starting.")
    admin_mobile = os.environ.get("ADMIN_MOBILE")
    admin_password = os.environ.get("ADMIN_PASSWORD")
    if admin_mobile and admin_password:
        conn = sqlite3.connect(DB_PATH)
        existing = conn.execute("SELECT id FROM users WHERE mobile=?", (admin_mobile,)).fetchone()
        if not existing:
            conn.execute("INSERT INTO users(name,mobile,password_hash,role) VALUES(?,?,?,?)",
                         ("VIP NEXUS Admin", admin_mobile, generate_password_hash(admin_password), "admin"))
            conn.commit()
        conn.close()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", "5000")), debug=False)
