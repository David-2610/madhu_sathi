import os
import json
import time
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models.user import User, UserRole
from app.models.beekeeper import BeekeeperProfile
from app.models.apiary import Apiary
from app.models.hive import Hive
from app.models.hive_device import HiveDevice
from app.core.security import hash_password

SQLALCHEMY_DATABASE_URL = "sqlite:///./real_test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def setup_hives():
    db = TestingSessionLocal()
    
    # 1. KVIC Admin
    kvic_user = User(full_name="KVIC Judge", phone="000", email="judge@kvic.in", password_hash=hash_password("123"), role=UserRole.KVIC_ADMIN, is_active=True)
    db.add(kvic_user)
    
    # 2. Beekeeper
    bk_user = User(full_name="Master Beekeeper", phone="111", email="bk@test.com", password_hash=hash_password("123"), role=UserRole.BEEKEEPER, is_active=True)
    db.add(bk_user)
    db.commit()
    db.refresh(bk_user)
    
    bk_profile = BeekeeperProfile(user_id=bk_user.id, beekeeper_code="BK-EXPERT")
    db.add(bk_profile)
    db.commit()
    db.refresh(bk_profile)
    
    apiary = Apiary(beekeeper_id=bk_profile.id, name="Test Apiary", location_name="Pune")
    db.add(apiary)
    db.commit()
    db.refresh(apiary)
    
    # 3. Create 3 Hives
    hive_a = Hive(apiary_id=apiary.id, hive_code="HIVE-A-NORMAL", hive_type="Langstroth")
    hive_b = Hive(apiary_id=apiary.id, hive_code="HIVE-B-SLIGHT", hive_type="Langstroth")
    hive_c = Hive(apiary_id=apiary.id, hive_code="HIVE-C-CRITICAL", hive_type="Langstroth")
    db.add_all([hive_a, hive_b, hive_c])
    db.commit()
    
    # Devices
    for h in [hive_a, hive_b, hive_c]:
        db.refresh(h)
        db.add(HiveDevice(hive_id=h.id, device_id=f"DEV-{h.hive_code}", is_active=True))
    db.commit()
    
    ha_id, hb_id, hc_id = hive_a.id, hive_b.id, hive_c.id
    db.close()
    return ha_id, hb_id, hc_id

def main():
    print("\nSTEP 1: START SYSTEM")
    h_a, h_b, h_c = setup_hives()
    print("Backend Database Initialized.")
    
    # Login
    resp = client.post("/auth/login", json={"email": "judge@kvic.in", "password": "123"})
    kvic_token = resp.json()["access_token"]
    
    resp_bk = client.post("/auth/login", json={"email": "bk@test.com", "password": "123"})
    bk_token = resp_bk.json()["access_token"]
    bk_headers = {"Authorization": f"Bearer {bk_token}"}
    
    print("\nSTEP 2: CONNECT WEBSOCKET AS KVIC ADMIN")
    with client.websocket_connect(f"/kvic/ws?token={kvic_token}") as websocket:
        print("WebSocket connected successfully!")
        
        # Read initial data
        initial = websocket.receive_json()
        print("\n--- INITIAL KVIC DASHBOARD DATA ---")
        print(json.dumps(initial["payload"]["overview"], indent=2))
        
        print("\nSTEP 3: SEND TELEMETRY TO HIVES")
        
        # HIVE A - NORMAL
        print("-> Sending normal telemetry to Hive A...")
        client.post(f"/beekeeper/hives/{h_a}/telemetry", json={
            "temperature_c": 35.0, "humidity_percent": 50.0, "weight_kg": 25.0, "sound_level": 40.0, "vibration_level": 0.1
        }, headers=bk_headers)
        
        # HIVE B - SLIGHT ISSUE
        print("-> Sending slight issue telemetry to Hive B (Humidity = 82%)...")
        client.post(f"/beekeeper/hives/{h_b}/telemetry", json={
            "temperature_c": 35.0, "humidity_percent": 82.0, "weight_kg": 25.0, "sound_level": 40.0, "vibration_level": 0.1
        }, headers=bk_headers)
        
        # HIVE C - CRITICAL
        print("-> Sending critical telemetry to Hive C (Temp = 45C, Weight Drop = 5kg)...")
        # First send normal to establish weight
        client.post(f"/beekeeper/hives/{h_c}/telemetry", json={
            "temperature_c": 35.0, "humidity_percent": 50.0, "weight_kg": 30.0, "sound_level": 40.0, "vibration_level": 0.1
        }, headers=bk_headers)
        time.sleep(0.1) # ensure order
        client.post(f"/beekeeper/hives/{h_c}/telemetry", json={
            "temperature_c": 45.0, "humidity_percent": 50.0, "weight_kg": 25.0, "sound_level": 70.0, "vibration_level": 1.5
        }, headers=bk_headers)
        
        print("\nSTEP 4: OBSERVE FULL FLOW (WEBSOCKET OUTPUT)", flush=True)
        
        events_received = []
        try:
            # 1 normal, 1 slight + alert + AI, 2 critical + 3 alerts + 1 AI = 9 events.
            for _ in range(9):
                msg = websocket.receive_json()
                events_received.append(msg)
        except Exception as e:
            pass # Timeout or end of stream
            
        for msg in events_received:
            print(f"\n[WS EVENT]: {msg['type']} (Hive {msg.get('hive_id', 'N/A')})", flush=True)
            if msg['type'] == 'ai-analysis':
                print(f"   Condition: {msg['payload']['condition_summary']}")
                print(f"   Expert Advice: {msg['payload']['explanation']}")
                print(f"   Action Steps: {msg['payload']['recommended_steps']}")
            elif msg['type'] == 'alert':
                print(f"   Alert [{msg['payload']['severity']}]: {msg['payload']['message']}")
            else:
                print(f"   Telemetry payload received.")

if __name__ == "__main__":
    main()
