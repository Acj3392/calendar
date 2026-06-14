#!/usr/bin/env python3
"""Generate data/spending.fake.json — a realistic but entirely invented dataset.

This mirrors the *structure* of the real data/spending.json (date range, the set of
categories, the budget-month keys, and the rough volume of transactions per day) but
NEVER copies any real amounts or merchant names. Every dollar figure here is invented
from the hardcoded ranges below, so the fake file leaks nothing about real spending.

The numbers are tuned to read like a ~$100k/yr earner: weighted everyday spend with
rare big-ticket items, recurring monthly bills, paychecks on the 1st/15th, and a
healthy mix of green / neutral / occasional-red days (not all overspent).

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
    "Mortgage": (1450, 1650),
    "Auto Payment": (280, 420),
    "Loan Repayment": (120, 300),
    "HOA": (150, 280),
    "Insurance": (70, 180),
    "Pet Insurance": (30, 55),
    "Gas & Electric": (45, 160),
    "Water": (25, 70),
    "Internet & Cable": (55, 95),
    "Business Utilities & Communication": (30, 90),
    "Groceries": (10, 65),
    "Restaurants & Bars": (10, 48),
    "Coffee Shops": (4, 9),
    "Coffee beans": (10, 22),
    "Beer & Liquor": (10, 45),
    "Gas": (24, 55),
    "EV Charge": (6, 22),
    "Parking & Tolls": (3, 18),
    "Taxi & Ride Shares": (8, 32),
    "Travel & Vacation": (45, 480),
    "Moving": (60, 350),
    "Amazon": (9, 70),
    "Shopping": (12, 110),
    "Clothing": (18, 95),
    "Furniture & Housewares": (25, 240),
    "Home Improvement": (12, 200),
    "New Home": (30, 380),
    "Office Supplies & Expenses": (7, 55),
    "Postage & Shipping": (4, 22),
    "Books": (9, 30),
    "Streaming": (8, 18),
    "Subscriptions": (5, 40),
    "Fitness": (12, 75),
    "Therapy": (70, 140),
    "Medical": (18, 180),
    "Pets": (10, 70),
    "Dog food": (22, 60),
    "Charity": (15, 90),
    "Gifts": (12, 90),
    "Entertainment & Recreation": (10, 80),
    "Fun Money": (8, 50),
    "Personal": (8, 55),
    "Cash & ATM": (40, 160),
    "Financial Fees": (2, 25),
    "Financial & Legal Services": (40, 220),
    "Interest": (1, 20),
    "Advertising & Promotion": (18, 140),
    "Miscellaneous": (5, 55),
    "Spanish Lessons": (22, 50),
}
DEFAULT_RANGE = (8, 60)

# Categories that represent money coming in (type "credit").
CREDIT_CATEGORIES = {"Paychecks", "Other Income", "Investments", "Interest"}

# Relative likelihood a transaction belongs to a category. Everyday spend is
# common; big-ticket items are rare so most days land green/neutral and only the
# occasional day trips the "overspent" threshold. Unlisted categories use 1.0.
WEIGHTS = {
    "Groceries": 9, "Restaurants & Bars": 8, "Coffee Shops": 7, "Gas": 4,
    "Amazon": 4, "Parking & Tolls": 3, "Taxi & Ride Shares": 3, "Subscriptions": 3,
    "Personal": 3, "Fun Money": 3, "Entertainment & Recreation": 3, "Shopping": 3,
    "Pets": 2, "Beer & Liquor": 2, "Coffee beans": 2, "EV Charge": 2, "Gifts": 2,
    "Books": 2, "Streaming": 2, "Fitness": 2, "Clothing": 2, "Office Supplies & Expenses": 2,
    "Miscellaneous": 2, "Postage & Shipping": 2, "Charity": 1, "Dog food": 1.5,
    # Big-ticket / recurring — deliberately rare as random picks (rent + utilities
    # are injected separately below so they recur predictably).
    "Travel & Vacation": 0.6, "Furniture & Housewares": 0.5, "Home Improvement": 0.5,
    "Medical": 0.5, "New Home": 0.3, "Moving": 0.2, "Financial & Legal Services": 0.3,
    "Cash & ATM": 0.8, "Therapy": 0.6, "Financial Fees": 0.5, "Advertising & Promotion": 0.3,
    "Spanish Lessons": 0.4,
}

# A ~$100k/yr earner: ~$3,150 take-home per paycheck, twice a month (~$75.6k
# net), plus modest other income → roughly six figures gross.
PAYCHECK = (3000, 3300)

# Recurring monthly bills, injected on fixed-ish days so they recur predictably
# (rather than appearing at random). (category, day-of-month, (min, max)).
MONTHLY_BILLS = [
    ("Mortgage", 1, (1450, 1650)),
    ("Gas & Electric", 8, (45, 160)),
    ("Internet & Cable", 12, (55, 95)),
    ("Water", 18, (25, 70)),
    ("Insurance", 22, (70, 180)),
    ("Subscriptions", 5, (8, 28)),
]

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
    # Triangular skewed toward the low end — most spend is small, big hits are rare.
    return round(rng.triangular(lo, hi, lo), 2)


def merchant_for(cat, rng):
    return rng.choice(MERCHANTS.get(cat, GENERIC_MERCHANTS))


def weighted_debit_category(debit_cats, rng):
    weights = [WEIGHTS.get(c, 1.0) for c in debit_cats]
    return rng.choices(debit_cats, weights=weights, k=1)[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (reproducible)")
    args = parser.parse_args()
    rng = random.Random(args.seed)

    with open(REAL) as f:
        real = json.load(f)

    # The category universe = every category seen in real transactions or budgets.
    seen_cats = {t["category"] for day in real["data"] for t in day["transactions"]}
    debit_cats = sorted(c for c in seen_cats if c not in CREDIT_CATEGORIES)
    fake_days = []
    for day in real["data"]:
        dom = int(day["date"][8:10])
        n = len(day["transactions"])
        # ~55% of days are "light" — a couple of small everyday purchases (green).
        if rng.random() < 0.55:
            n = rng.randint(1, 3)
        else:
            n = min(n, 5)  # thin out the heaviest days for a realistic spend total

        txns = []
        for _ in range(n):
            cat = weighted_debit_category(debit_cats, rng)
            txns.append({
                "merchant": merchant_for(cat, rng),
                "amount": amount_for(cat, rng),
                "category": cat,
                "type": "debit",
            })

        # Inject recurring monthly bills on their due day.
        for cat, due, (lo, hi) in MONTHLY_BILLS:
            if dom == due:
                txns.append({
                    "merchant": merchant_for(cat, rng),
                    "amount": round(rng.uniform(lo, hi), 2),
                    "category": cat,
                    "type": "debit",
                })

        # Inject paychecks on the 1st and 15th, plus the rare bit of other income.
        if dom in (1, 15):
            txns.append({
                "merchant": merchant_for("Paychecks", rng),
                "amount": round(rng.uniform(*PAYCHECK), 2),
                "category": "Paychecks",
                "type": "credit",
            })
        elif rng.random() < 0.03:
            txns.append({
                "merchant": merchant_for("Other Income", rng),
                "amount": round(rng.uniform(40, 220), 2),
                "category": "Other Income",
                "type": "credit",
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
