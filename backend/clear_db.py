"""
Clear all data from all tables while keeping the schema intact.
No seeding - just a clean empty database.
"""
import os
from dotenv import load_dotenv
load_dotenv()

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")
print("Connecting to database...")

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = False
cur = conn.cursor()

# Disable FK checks temporarily, delete all data, re-enable
try:
    # Get all table names in the public schema
    cur.execute("""
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public'
        ORDER BY tablename;
    """)
    tables = [row[0] for row in cur.fetchall()]
    print(f"Found {len(tables)} tables: {tables}")

    # Truncate all tables at once with CASCADE (handles foreign keys)
    if tables:
        table_list = ", ".join(tables)
        cur.execute(f"TRUNCATE TABLE {table_list} RESTART IDENTITY CASCADE;")
        conn.commit()
        print("\n✅ All tables cleared successfully!")
        print("✅ Schema (tables, columns, indexes) is fully intact.")
        print("✅ Database is now empty and ready for fresh use.")
    else:
        print("No tables found.")

except Exception as e:
    conn.rollback()
    print(f"❌ Error: {e}")
finally:
    cur.close()
    conn.close()
