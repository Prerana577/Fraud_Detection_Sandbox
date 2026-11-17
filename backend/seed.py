"""
seed.py — Populates the database with 50 realistic Indian cardholders.

Run once after `flask db upgrade` (or app startup which auto-creates tables):
    python seed.py

The script is idempotent: it skips users that already exist.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from models import db, User

# ─── Indian city data ─────────────────────────────────────────────────────────
# Each entry: (city_name, lat, lon, typical_avg_amount_INR)
CITIES = [
    ("Bengaluru",  12.9716,  77.5946, 3500),
    ("Mumbai",     19.0760,  72.8777, 4500),
    ("Delhi",      28.6139,  77.2090, 4000),
    ("Chennai",    13.0827,  80.2707, 3200),
    ("Hyderabad",  17.3850,  78.4867, 3800),
    ("Pune",       18.5204,  73.8567, 3600),
    ("Kolkata",    22.5726,  88.3639, 2800),
    ("Guwahati",   26.1445,  91.7362, 2200),
    ("Jaipur",     26.9124,  75.7873, 2500),
    ("Ahmedabad",  23.0225,  72.5714, 3000),
]

# 50 seeded users (5 per city)
USERS = [
    # Bengaluru
    {"name": "Arjun Sharma",       "city": "Bengaluru",  "avg": 3800},
    {"name": "Priya Nair",         "city": "Bengaluru",  "avg": 2900},
    {"name": "Rohan Mehta",        "city": "Bengaluru",  "avg": 5100},
    {"name": "Divya Krishnamurthy","city": "Bengaluru",  "avg": 1800},
    {"name": "Kiran Reddy",        "city": "Bengaluru",  "avg": 4200},
    # Mumbai
    {"name": "Neha Desai",         "city": "Mumbai",     "avg": 6200},
    {"name": "Amit Patil",         "city": "Mumbai",     "avg": 3900},
    {"name": "Sunita Joshi",       "city": "Mumbai",     "avg": 5500},
    {"name": "Rahul Kapoor",       "city": "Mumbai",     "avg": 7800},
    {"name": "Anjali Menon",       "city": "Mumbai",     "avg": 4100},
    # Delhi
    {"name": "Vikram Singh",       "city": "Delhi",      "avg": 5200},
    {"name": "Kavita Yadav",       "city": "Delhi",      "avg": 3300},
    {"name": "Manish Gupta",       "city": "Delhi",      "avg": 4900},
    {"name": "Pooja Sharma",       "city": "Delhi",      "avg": 2600},
    {"name": "Rajesh Kumar",       "city": "Delhi",      "avg": 6100},
    # Chennai
    {"name": "Lakshmi Venkat",     "city": "Chennai",    "avg": 3400},
    {"name": "Suresh Iyer",        "city": "Chennai",    "avg": 2800},
    {"name": "Meena Balasubramanian","city": "Chennai",  "avg": 4200},
    {"name": "Ganesh Pillai",      "city": "Chennai",    "avg": 3100},
    {"name": "Saranya Ramesh",     "city": "Chennai",    "avg": 5300},
    # Hyderabad
    {"name": "Sridhar Rao",        "city": "Hyderabad",  "avg": 4400},
    {"name": "Padma Reddy",        "city": "Hyderabad",  "avg": 3700},
    {"name": "Anil Kumar",         "city": "Hyderabad",  "avg": 5900},
    {"name": "Bhavana Chandra",    "city": "Hyderabad",  "avg": 2900},
    {"name": "Naresh Goud",        "city": "Hyderabad",  "avg": 3500},
    # Pune
    {"name": "Swapnil Kulkarni",   "city": "Pune",       "avg": 3900},
    {"name": "Sneha Deshpande",    "city": "Pune",       "avg": 2700},
    {"name": "Prasad Bhosale",     "city": "Pune",       "avg": 4600},
    {"name": "Rupali Pawar",       "city": "Pune",       "avg": 3200},
    {"name": "Gaurav More",        "city": "Pune",       "avg": 5100},
    # Kolkata
    {"name": "Debashis Ghosh",     "city": "Kolkata",    "avg": 3100},
    {"name": "Arpita Banerjee",    "city": "Kolkata",    "avg": 2500},
    {"name": "Sourav Chatterjee",  "city": "Kolkata",    "avg": 4000},
    {"name": "Pritha Sen",         "city": "Kolkata",    "avg": 2900},
    {"name": "Rajib Das",          "city": "Kolkata",    "avg": 3700},
    # Guwahati
    {"name": "Bhaskar Baruah",     "city": "Guwahati",   "avg": 2400},
    {"name": "Dipali Borah",       "city": "Guwahati",   "avg": 1900},
    {"name": "Pranab Gogoi",       "city": "Guwahati",   "avg": 2800},
    {"name": "Mitali Deka",        "city": "Guwahati",   "avg": 2100},
    {"name": "Himanta Kalita",     "city": "Guwahati",   "avg": 3300},
    # Jaipur
    {"name": "Mahesh Sharma",      "city": "Jaipur",     "avg": 2700},
    {"name": "Savitri Agarwal",    "city": "Jaipur",     "avg": 2300},
    {"name": "Deepak Verma",       "city": "Jaipur",     "avg": 3400},
    {"name": "Rekha Gupta",        "city": "Jaipur",     "avg": 1900},
    {"name": "Sunil Chauhan",      "city": "Jaipur",     "avg": 2800},
    # Ahmedabad
    {"name": "Hitesh Patel",       "city": "Ahmedabad",  "avg": 3200},
    {"name": "Rima Shah",          "city": "Ahmedabad",  "avg": 2600},
    {"name": "Chirag Trivedi",     "city": "Ahmedabad",  "avg": 4100},
    {"name": "Nita Jain",          "city": "Ahmedabad",  "avg": 2800},
    {"name": "Jayesh Pandya",      "city": "Ahmedabad",  "avg": 3600},
]

# Build a quick city-lookup dict
_CITY_MAP = {c[0]: {"lat": c[1], "lon": c[2]} for c in CITIES}


def seed_users():
    """Insert seed users if they don't already exist."""
    created = 0
    for u in USERS:
        city_data = _CITY_MAP[u["city"]]
        # Check for duplicates by name (safe for seed data)
        existing = User.query.filter_by(name=u["name"]).first()
        if existing:
            continue
        user = User(
            name=u["name"],
            home_city=u["city"],
            home_lat=city_data["lat"],
            home_lon=city_data["lon"],
            avg_amount=float(u["avg"]),
            status="active",
        )
        db.session.add(user)
        created += 1

    db.session.commit()
    print(f"[seed] Created {created} new users ({len(USERS) - created} already existed).")


if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()
        seed_users()
        print("[seed] Done.")
