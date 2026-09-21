"""
Test local FastAPI server's AI assistant endpoint end-to-end.
"""

import requests
from app.db import SessionLocal
from app.models.user import User, UserRole
from app.models.beekeeper import BeekeeperProfile
from app.models.hive import Hive
from app.core.security import create_access_token

db = SessionLocal()
try:
    beekeeper = db.query(BeekeeperProfile).first()
    if not beekeeper:
        print("[!] No beekeeper profile found in DB.")
        exit(1)

    user = db.query(User).filter(User.id == beekeeper.user_id).first()
    hive = db.query(Hive).filter(Hive.apiary.has(beekeeper_id=beekeeper.id)).first()
    if not hive:
        print(f"[!] No hive found for beekeeper id {beekeeper.id}.")
        exit(1)

    print(f"[*] Found beekeeper user: {user.email} (ID: {user.id})")
    print(f"[*] Found hive: {hive.hive_code} (ID: {hive.id})")

    token = create_access_token(user.id)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = f"http://127.0.0.1:8000/beekeeper/hives/{hive.id}/assistant"
    payload = {
        "query": "Is there any risk of swarming or overheating based on current readings?"
    }

    print(f"[*] Sending POST request to {url}...")
    resp = requests.post(url, json=payload, headers=headers, timeout=25)
    print("HTTP Status:", resp.status_code)
    if resp.status_code == 200:
        data = resp.json()
        print("\n[SUCCESS] Response from Local Server:")
        print(f"  Hive ID: {data.get('hive_id')}")
        print(f"  Provider: {data.get('provider')}")
        print(f"  Is Mock: {data.get('is_mock')}")
        print(f"  Condition Summary: {data.get('condition_summary')}")
        print(f"  Explanation: {data.get('explanation')}")
        print(f"  Recommended Steps:")
        for idx, step in enumerate(data.get('recommended_steps', []), 1):
            print(f"    {idx}. {step}")
        print(f"  Disclaimer: {data.get('disclaimer')}")
    else:
        print("Error Response:", resp.text)

finally:
    db.close()
