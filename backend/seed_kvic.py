"""
Seed KVIC Dashboard Data directly to Supabase via psycopg2.
This bypasses the deleted local backend codebase and inserts raw SQL.
"""
import os
import psycopg2
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
print("Connecting to database...")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

try:
    now = datetime.now(timezone.utc)
    
    # 1. Create a Beekeeper user (test2)
    cur.execute("""
        INSERT INTO users (full_name, email, phone, password_hash, role, is_active, created_at, updated_at)
        VALUES ('Test Beekeeper', 'test2@gamil.com', '1234567890', '$2b$12$6/7aFw/9TInyB4R1d29lUud2iZ7rI9n81u4YxG.R2O931fE1xK.Z.', 'BEEKEEPER', true, %s, %s)
        RETURNING id;
    """, (now, now))
    bk_id = cur.fetchone()[0]
    
    # Create KVIC user (test3)
    cur.execute("""
        INSERT INTO users (full_name, email, phone, password_hash, role, is_active, created_at, updated_at)
        VALUES ('KVIC Admin', 'test3@gamil.com', '0987654321', '$2b$12$6/7aFw/9TInyB4R1d29lUud2iZ7rI9n81u4YxG.R2O931fE1xK.Z.', 'KVIC_ADMIN', true, %s, %s);
    """, (now, now))

    # 2. Create Beekeeper Profile
    cur.execute("""
        INSERT INTO beekeeper_profiles (user_id, beekeeper_code, experience_years, created_at, updated_at)
        VALUES (%s, 'BK-001', 5, %s, %s)
        RETURNING id;
    """, (bk_id, now, now))
    bp_id = cur.fetchone()[0]
    
    # 3. Create an Apiary
    cur.execute("""
        INSERT INTO apiaries (beekeeper_id, name, location_name, latitude, longitude, created_at, updated_at)
        VALUES (%s, 'KVIC Demo Apiary', 'Nashik, Maharashtra', 20.0, 73.7, %s, %s)
        RETURNING id;
    """, (bp_id, now, now))
    apiary_id = cur.fetchone()[0]
    
    # 4. Create 3 Hives
    hive_ids = []
    for i in range(1, 4):
        cur.execute("""
            INSERT INTO hives (apiary_id, hive_code, hive_type, status, created_at, updated_at)
            VALUES (%s, %s, 'LANGSTROTH', 'ACTIVE', %s, %s)
            RETURNING id;
        """, (apiary_id, f'HIVE-00{i}', now, now))
        hive_ids.append(cur.fetchone()[0])
        
    # 5. Create some telemetry data for the last 5 hours so graphs work
    print(f"Created Hives: {hive_ids}")
    for h_id in hive_ids:
        for hours_ago in range(5, -1, -1):
            ts = now - timedelta(hours=hours_ago)
            # Add some variance
            temp = 34.0 + (h_id * 0.5)
            hum = 55.0 + (h_id * 2.0)
            weight = 25.0 + (hours_ago * 0.1) # Weight decreasing slightly? Or increasing
            
            cur.execute("""
                INSERT INTO hive_telemetry (hive_id, timestamp, temperature_c, humidity_percent, weight_kg, sound_level, vibration_level, is_simulated, created_at)
                VALUES (%s, %s, %s, %s, %s, 50.0, 1.0, true, %s);
            """, (h_id, ts, temp, hum, weight, ts))
            
    # 6. Create IoT Hive States (for the mock server)
    for h_id in hive_ids:
        cur.execute("""
            INSERT INTO iot_hive_states (hive_id, temperature, humidity, weight, sound_level, co2_level, activity_level, status, last_updated)
            VALUES (%s, 35.0, 60.0, 25.0, 50.0, 700.0, 'Normal', 'Healthy', %s);
        """, (h_id, now))
        
    conn.commit()
    print("✅ Successfully seeded database with KVIC dummy data!")
    print("KVIC Dashboard should now display 1 Apiary, 3 Hives, and telemetry data.")

except Exception as e:
    conn.rollback()
    print(f"❌ Error seeding data: {e}")
finally:
    cur.close()
    conn.close()
