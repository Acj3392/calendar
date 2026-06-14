#!/usr/bin/env python3
"""Generate data/spending.fake.json — a "mirror" of the real data, scaled down.

This keeps the *shape* of data/spending.json (each day's transactions, their
categories and debit/credit type, and the budget structure) so the fake calendar
reads like real life — but every merchant is swapped for an invented one and every
amount is scaled down, with a little random jitter so the numbers are not a clean,
reversible multiple of the originals.

Adjustments beyond a flat scale:
- Groceries scaled further (two-person household).
- Pet categories scaled way down.
- Only ONE mortgage payment is kept per month (the real data has two).

Note: because amounts derive from the real ones, this fake set *approximates* the
real spending distribution — intentional (the goal is realism), but it means it is
not fully decoupled from the real data the way a from-scratch synthetic set would be.

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

# How much to scale each real amount down. Most categories use DEFAULT_SCALE.
# Jitter (±8%) keeps amounts from being a clean, reversible multiple of the real ones.
DEFAULT_SCALE = 0.88
CATEGORY_SCALE = {
    "Groceries": 0.78,      # two-person household
    "Pets": 0.30,           # way less pet spend
    "Dog food": 0.30,
    "Pet Insurance": 0.40,
}
JITTER = 0.08

# Keep at most this many of a category's transactions per month (others dropped).
# The real data carries two mortgages; the fake persona has one.
MONTHLY_CAP = {"Mortgage": 1}

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
    "Cash & ATM": ["Quickdraw ATM", "Mainline Cash"],
}
GENERIC_MERCHANTS = ["Maple & Co.", "Corner Shop", "Downtown Co-op", "Sundry Goods"]


def scale_for(cat):
    return CATEGORY_SCALE.get(cat, DEFAULT_SCALE)


def merchant_for(cat, rng):
    return rng.choice(MERCHANTS.get(cat, GENERIC_MERCHANTS))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="RNG seed (reproducible)")
    args = parser.parse_args()
    rng = random.Random(args.seed)

    with open(REAL) as f:
        real = json.load(f)

    # Per-month counts so we can cap categories like Mortgage to one a month.
    month_counts = {}
    fake_days = []
    for day in real["data"]:
        month = day["date"][:7]
        seen = month_counts.setdefault(month, {})
        txns = []
        for t in day["transactions"]:
            cat = t["category"]
            cap = MONTHLY_CAP.get(cat)
            if cap is not None:
                seen[cat] = seen.get(cat, 0) + 1
                if seen[cat] > cap:
                    continue  # drop the extra (e.g. second mortgage)
            amt = abs(t["amount"]) * scale_for(cat) * rng.uniform(1 - JITTER, 1 + JITTER)
            txns.append({
                "merchant": merchant_for(cat, rng),
                "amount": round(amt, 2),
                "category": cat,
                "type": t["type"],
            })
        total = round(sum(x["amount"] for x in txns if x["type"] == "debit"), 2)
        received = round(sum(x["amount"] for x in txns if x["type"] == "credit"), 2)
        fake_days.append({
            "date": day["date"],
            "total": total,
            "received": received,
            "net": round(total - received, 2),
            "transactions": txns,
        })

    # Budgets: mirror the real category budgets, scaled the same way. Mortgage is
    # halved on top of its scale since the fake persona carries a single mortgage.
    fake_budgets = {}
    for month, cats in real["budgets"].items():
        fake_budgets[month] = {}
        for cat, planned in cats.items():
            val = planned * scale_for(cat)
            if cat == "Mortgage":
                val *= 0.5
            fake_budgets[month][cat] = int(round(val / 25.0) * 25)

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
