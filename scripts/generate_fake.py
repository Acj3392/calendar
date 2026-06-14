#!/usr/bin/env python3
"""Generate data/spending.fake.json — a realistic but entirely invented dataset.

This mirrors the *structure* of the real data/spending.json (date range, the set of
categories, the budget-month keys, and the number of transactions per day) but NEVER
copies any real amounts or merchant names. Every dollar figure here is invented from
the hardcoded ranges below, so the fake file leaks nothing about real spending.

Usage:
    python3 scripts/generate_fake.py            # uses default seed (reproducible)
    python3 scripts/generate_fake.py --seed 7   # different reproducible dataset
"""
import argparse
import json
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REAL = os.path.join(ROOT, "data", "spending.json")
FAKE = os.path.join(ROOT, "data", "spending.fake.json")

# Plausible (min, max) amount ranges per category, fully decoupled from real data.
# Categories not listed fall back to DEFAULT_RANGE. Income categories are listed in
# CREDIT_CATEGORIES below and produce money-in (type "credit").
RANGES = {
    "Mortgage": (1800, 2600),
    "Auto Payment": (350, 520),
    "Loan Repayment": (150, 400),
    "HOA": (200, 350),
    "Insurance": (90, 260),
    "Pet Insurance": (35, 70),
    "Gas & Electric": (60, 220),
    "Water": (25, 90),
    "Internet & Cable": (60, 130),
    "Business Utilities & Communication": (40, 160),
    "Groceries": (18, 145),
    "Restaurants & Bars": (16, 120),
    "Coffee Shops": (4, 12),
    "Coffee beans": (12, 28),
    "Beer & Liquor": (12, 65),
    "Gas": (28, 78),
    "EV Charge": (8, 35),
    "Parking & Tolls": (3, 28),
    "Taxi & Ride Shares": (9, 45),
    "Travel & Vacation": (60, 850),
    "Moving": (80, 600),
    "Amazon": (10, 120),
    "Shopping": (15, 200),
    "Clothing": (20, 180),
    "Furniture & Housewares": (30, 450),
    "Home Improvement": (15, 380),
    "New Home": (40, 700),
    "Office Supplies & Expenses": (8, 90),
    "Postage & Shipping": (4, 35),
    "Books": (10, 45),
    "Streaming": (8, 25),
    "Subscriptions": (5, 60),
    "Fitness": (15, 120),
    "Therapy": (90, 200),
    "Medical": (20, 350),
    "Pets": (12, 110),
    "Dog food": (25, 80),
    "Charity": (20, 200),
    "Gifts": (15, 150),
    "Entertainment & Recreation": (12, 140),
    "Fun Money": (10, 80),
    "Personal": (8, 90),
    "Cash & ATM": (40, 300),
    "Financial Fees": (2, 40),
    "Financial & Legal Services": (50, 400),
    "Interest": (1, 30),
    "Advertising & Promotion": (20, 250),
    "Miscellaneous": (5, 75),
    "Spanish Lessons": (25, 60),
}
DEFAULT_RANGE = (10, 90)

# Categories that represent money coming in (type "credit").
CREDIT_CATEGORIES = {"Paychecks", "Other Income", "Investments", "Interest"}

# Invented merchant pools per category. A category with no pool uses GENERIC_MERCHANTS.
MERCHANTS = {
    "Mortgage": ["Cedar Trust Home Loans"],
    "Auto Payment": ["Northwind Auto Finance"],
    "Groceries": ["Greenfield Market", "Harvest Lane Grocers", "Cobblestone Foods"],
    "Restaurants & Bars": ["The Copper Fork", "Lantern & Oak", "Rosewood Tavern", "Blue Heron Cafe"],
    "Coffee Shops": ["Morning Tide Coffee", "Acorn & Bean", "Foglight Roasters"],
    "Coffee beans": ["Foglight Roasters"],
    "Beer & Liquor": ["Hopvale Bottle Shop"],
    "Gas": ["Summit Fuel", "Riverside Gas"],
    "EV Charge": ["VoltWay Charging"],
    "Amazon": ["Parcelhaus"],
    "Shopping": ["Marlowe Goods", "Tinder Box Mercantile"],
    "Clothing": ["Aspen Threads", "Field & Stitch"],
    "Furniture & Housewares": ["Hearthstone Home", "Maple & Co."],
    "Home Improvement": ["Builder's Yard", "Stonepath Hardware"],
    "Streaming": ["StreamArc", "Nimbus TV"],
    "Subscriptions": ["Cloudpeak", "Inkwell Digital"],
    "Fitness": ["Ironwood Gym", "Pulse Studio"],
    "Therapy": ["Stillwater Counseling"],
    "Medical": ["Lakeside Clinic", "Brightleaf Medical"],
    "Pets": ["Whiskers & Paws", "Tailwag Supply"],
    "Dog food": ["Tailwag Supply"],
    "Travel & Vacation": ["Wanderline Travel", "Harbor View Inn", "SkyReach Air"],
    "Gas & Electric": ["Valley Power & Light"],
    "Water": ["Municipal Water Dist."],
    "Internet & Cable": ["Fibernet"],
    "Charity": ["Open Hands Fund", "Rivertown Shelter"],
    "Gifts": ["The Gift Loft"],
    "Taxi & Ride Shares": ["ZipRide"],
    "Paychecks": ["Employer Payroll"],
    "Other Income": ["Misc Income"],
    "Investments": ["Brokerage Transfer"],
    "Interest": ["Savings Interest"],
    "Cash & ATM": ["ATM Withdrawal"],
}
GENERIC_MERCHANTS = ["Maple & Co.", "Corner Shop", "Downtown Co-op", "Sundry Goods"]


def amount_for(cat, rng):
    lo, hi = RANGES.get(cat, DEFAULT_RANGE)
    # Two decimals, like real transaction amounts.
    return round(rng.uniform(lo, hi), 2)


def merchant_for(cat, rng):
    return rng.choice(MERCHANTS.get(cat, GENERIC_MERCHANTS))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (reproducible)")
    args = parser.parse_args()
    rng = random.Random(args.seed)

    with open(REAL) as f:
        real = json.load(f)

    # The category universe = every category seen in real transactions or budgets.
    seen_cats = {t["category"] for day in real["data"] for t in day["transactions"]}
    fake_days = []
    for day in real["data"]:
        n = len(day["transactions"])
        txns = []
        for _ in range(n):
            cat = rng.choice(sorted(seen_cats))
            is_credit = cat in CREDIT_CATEGORIES
            amt = amount_for(cat, rng)
            if is_credit:
                # Income is larger; scale paychecks up notably.
                amt = round(amt * (rng.uniform(30, 60) if cat == "Paychecks" else rng.uniform(2, 6)), 2)
            txns.append({
                "merchant": merchant_for(cat, rng),
                "amount": amt,
                "category": cat,
                "type": "credit" if is_credit else "debit",
            })
        total = round(sum(t["amount"] for t in txns if t["type"] == "debit"), 2)
        received = round(sum(t["amount"] for t in txns if t["type"] == "credit"), 2)
        fake_days.append({
            "date": day["date"],
            "total": total,
            "received": received,
            "net": round(total - received, 2),
            "transactions": txns,
        })

    # Fake budgets: same month + category keys as real, plausible round numbers.
    fake_budgets = {}
    for month, cats in real["budgets"].items():
        fake_budgets[month] = {}
        for cat in cats:
            lo, hi = RANGES.get(cat, DEFAULT_RANGE)
            # Monthly budget ~ a handful of typical transactions, rounded to $25.
            base = (lo + hi) / 2 * rng.uniform(3, 8)
            fake_budgets[month][cat] = int(round(base / 25.0) * 25)

    fake = {
        "today": real.get("today"),
        "generatedAt": "demo",
        "refreshStatus": "Demo data — not real spending.",
        "budgets": fake_budgets,
        "data": fake_days,
    }

    with open(FAKE, "w") as f:
        json.dump(fake, f, separators=(",", ":"))
    print(f"Wrote {FAKE} — {len(fake_days)} days, seed={args.seed}")


if __name__ == "__main__":
    main()
