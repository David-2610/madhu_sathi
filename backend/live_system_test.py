import json
import time
import requests
import asyncio
import websockets

BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000"

async def ws_loop(kvic_token):
    print("\nSTEP 2: CONNECT WEBSOCKET AS KVIC ADMIN")
    async with websockets.connect(f"{WS_URL}/kvic/ws?token={kvic_token}") as websocket:
        print("WebSocket connected successfully!")
        
        initial_str = await websocket.recv()
        initial = json.loads(initial_str)
        print("\n--- INITIAL KVIC DASHBOARD DATA ---")
        print(json.dumps(initial["payload"]["overview"], indent=2))
        
        print("\nSTEP 4: OBSERVE FULL FLOW (WEBSOCKET OUTPUT WITH GENUINE GEMINI AI)", flush=True)
        
        for _ in range(9):
            try:
                msg_str = await asyncio.wait_for(websocket.recv(), timeout=15.0)
                msg = json.loads(msg_str)
                print(f"\n[WS EVENT]: {msg['type']} (Hive {msg.get('hive_id', 'N/A')})", flush=True)
                if msg['type'] == 'ai-analysis':
                    print(f"   Condition: {msg['payload']['condition_summary']}")
                    print(f"   Expert Advice: {msg['payload']['explanation']}")
                    print(f"   Action Steps: {msg['payload']['recommended_steps']}")
                    print(f"   AI Provider: {msg['payload'].get('provider', 'UNKNOWN')}")
                elif msg['type'] == 'alert':
                    print(f"   Alert [{msg['payload']['severity']}]: {msg['payload']['message']}")
                else:
                    print(f"   Telemetry payload received.")
            except asyncio.TimeoutError:
                print("WS Read Timeout")
                break
            except Exception as e:
                print(f"WS Error: {e}")
                break

def main():
    print("\nSTEP 1: LOGIN / REGISTER USERS")
    
    requests.post(f"{BASE_URL}/auth/register", json={"email": "live_judge@kvic.in", "password": "123", "role": "KVIC_ADMIN"})
    resp_kvic = requests.post(f"{BASE_URL}/auth/login", json={"email": "live_judge@kvic.in", "password": "123"})
    if resp_kvic.status_code != 200:
        print("Failed to login KVIC Admin:", resp_kvic.text)
        return
    kvic_token = resp_kvic.json()["access_token"]
    
    requests.post(f"{BASE_URL}/auth/register", json={"email": "live_bk@test.com", "password": "123", "role": "BEEKEEPER"})
    resp_bk = requests.post(f"{BASE_URL}/auth/login", json={"email": "live_bk@test.com", "password": "123"})
    bk_token = resp_bk.json()["access_token"]
    bk_headers = {"Authorization": f"Bearer {bk_token}"}
    
    apiary_resp = requests.post(f"{BASE_URL}/beekeeper/apiaries", json={"name": "Live Test Apiary", "location_name": "Pune"}, headers=bk_headers)
    if apiary_resp.status_code == 201:
        apiary_id = apiary_resp.json()["id"]
    else:
        apiaries = requests.get(f"{BASE_URL}/beekeeper/apiaries", headers=bk_headers).json()
        if apiaries:
            apiary_id = apiaries[0]["id"]
        else:
            print("Failed to get/create apiary")
            return
            
    hives = []
    for code in ["LIVE-HIVE-A", "LIVE-HIVE-B", "LIVE-HIVE-C"]:
        resp = requests.post(f"{BASE_URL}/beekeeper/hives", json={"apiary_id": apiary_id, "hive_code": code, "hive_type": "Langstroth"}, headers=bk_headers)
        if resp.status_code == 201:
            hives.append(resp.json()["id"])
        else:
            all_hives = requests.get(f"{BASE_URL}/beekeeper/apiaries/{apiary_id}/hives", headers=bk_headers).json()
            for h in all_hives:
                if h["hive_code"] == code:
                    hives.append(h["id"])
                    
    h_a, h_b, h_c = hives[0], hives[1], hives[2]
    
    print("\nSTEP 3: SEND TELEMETRY TO HIVES (USING GEMINI)")
    
    # Send telemetry data now! We will just fire it after a small delay.
    # To capture it on WS, we must start WS loop and THEN send telemetry.
    async def run_all():
        ws_task = asyncio.create_task(ws_loop(kvic_token))
        await asyncio.sleep(1) # wait for ws to connect
        
        print("-> Sending normal telemetry to Hive A...")
        requests.post(f"{BASE_URL}/beekeeper/hives/{h_a}/telemetry", json={
            "temperature_c": 35.0, "humidity_percent": 50.0, "weight_kg": 25.0, "sound_level": 40.0, "vibration_level": 0.1
        }, headers=bk_headers)
        
        print("-> Sending slight issue telemetry to Hive B (Humidity = 82%)...")
        requests.post(f"{BASE_URL}/beekeeper/hives/{h_b}/telemetry", json={
            "temperature_c": 35.0, "humidity_percent": 82.0, "weight_kg": 25.0, "sound_level": 40.0, "vibration_level": 0.1
        }, headers=bk_headers)
        
        print("-> Sending critical telemetry to Hive C (Temp = 45C, Weight Drop = 5kg)...")
        requests.post(f"{BASE_URL}/beekeeper/hives/{h_c}/telemetry", json={
            "temperature_c": 35.0, "humidity_percent": 50.0, "weight_kg": 30.0, "sound_level": 40.0, "vibration_level": 0.1
        }, headers=bk_headers)
        time.sleep(1)
        requests.post(f"{BASE_URL}/beekeeper/hives/{h_c}/telemetry", json={
            "temperature_c": 45.0, "humidity_percent": 50.0, "weight_kg": 25.0, "sound_level": 70.0, "vibration_level": 1.5
        }, headers=bk_headers)
        
        await ws_task
        
    asyncio.run(run_all())

if __name__ == "__main__":
    main()
