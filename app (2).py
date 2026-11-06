# Student Budget Buddy
# Tools: Python, Flask, MongoDB
#
# What it does:
#   1. You set a monthly budget
#   2. You add your expenses (food, travel, etc.)
#   3. The page shows your total, money left, spending per category
#      and a warning when you are close to your budget

from datetime import date

from bson import ObjectId
from flask import Flask, redirect, render_template, request
from pymongo import MongoClient

app = Flask(__name__)

# Your MongoDB link is kept in a private file called config.py
# (copy config_example.py, rename the copy to config.py, add your link)
try:
    from config import MONGO_URI
except ImportError:
    raise SystemExit("config.py not found. Copy config_example.py to config.py and add your MongoDB link.")

# Connect to the database
client = MongoClient(MONGO_URI)
db = client["budget_db"]
expenses_collection = db["expenses"]    # stores every expense
settings_collection = db["settings"]    # stores the monthly budget

# The categories shown in the dropdown
CATEGORIES = ["Food", "Travel", "Subscriptions", "Shopping", "Education", "Other"]


# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def get_budget():
    """Read the monthly budget from the database (0 if not set yet)."""
    setting = settings_collection.find_one({"name": "monthly_budget"})
    if setting is None:
        return 0
    return setting["amount"]


def get_date(expense):
    """Used for sorting: returns the date of an expense."""
    return expense["date"]


# ------------------------------------------------------------
# Routes (web pages)
# ------------------------------------------------------------
@app.route("/")
def home():
    this_month = date.today().strftime("%Y-%m")   # example: 2026-11
    budget = get_budget()

    # Collect only this month's expenses
    expenses = []
    for item in expenses_collection.find({}):
        if item["date"].startswith(this_month):
            expenses.append({
                "id": str(item["_id"]),
                "title": item["title"],
                "amount": item["amount"],
                "category": item["category"],
                "date": item["date"],
            })

    # Newest expense first
    expenses.sort(key=get_date, reverse=True)

    # Add up the total, and the total for each category
    total = 0
    by_category = {}
    for e in expenses:
        total = total + e["amount"]
        if e["category"] in by_category:
            by_category[e["category"]] = by_category[e["category"]] + e["amount"]
        else:
            by_category[e["category"]] = e["amount"]

    # Money left and percentage used
    left = budget - total
    if budget > 0:
        percent_used = round(total / budget * 100)
    else:
        percent_used = 0

    # Decide the colour/status of the progress bar
    if budget == 0:
        status = "none"
    elif percent_used >= 100:
        status = "danger"
    elif percent_used >= 80:
        status = "warning"
    else:
        status = "safe"

    return render_template(
        "index.html",
        categories=CATEGORIES,
        expenses=expenses,
        budget=budget,
        total=total,
        left=left,
        percent_used=percent_used,
        bar_width=min(percent_used, 100),
        status=status,
        by_category=by_category,
        month_name=date.today().strftime("%B %Y"),
        today=date.today().isoformat(),
    )


@app.route("/budget", methods=["POST"])
def set_budget():
    try:
        amount = float(request.form.get("budget", "0"))
    except ValueError:
        amount = 0

    if amount > 0:
        # update_one with upsert=True: update if it exists, otherwise create it
        settings_collection.update_one(
            {"name": "monthly_budget"},
            {"$set": {"amount": amount}},
            upsert=True,
        )
    return redirect("/")


@app.route("/add", methods=["POST"])
def add_expense():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "Other")
    expense_date = request.form.get("date", "")

    try:
        amount = float(request.form.get("amount", "0"))
    except ValueError:
        amount = 0

    # Save only if the data is valid
    if title != "" and amount > 0 and expense_date != "":
        expenses_collection.insert_one({
            "title": title,
            "amount": amount,
            "category": category,
            "date": expense_date,
        })
    return redirect("/")


@app.route("/delete/<expense_id>", methods=["POST"])
def delete_expense(expense_id):
    expenses_collection.delete_one({"_id": ObjectId(expense_id)})
    return redirect("/")


# ------------------------------------------------------------
# Start the app
# ------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)