import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import Base, engine, SessionLocal
from app.models.apiary import Apiary
from app.models.beekeeper import BeekeeperProfile
from app.models.hive import Hive, HiveStatus
from app.models.iot_hive_state import IoTHiveState
from app.models.user import User
from app.schemas.user import UserRole
from app.models.honey_harvest import HoneyHarvest
from app.models.honey_batch import HoneyBatch, BatchStatus
from app.models.honey_product import HoneyProduct, ProductStatus
from app.crud.traceability_event import record_event
from app.models.traceability_event import TraceEventType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_db():
    logger.info("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    logger.info("Recreating all tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema reset complete.")

def seed_data():
    with SessionLocal() as db:
        logger.info("Seeding Test Users...")
        # 1. KVIC Admin
        kvic_user = User(
            email="test1@gamil.com",
            phone="1234567890",
            password_hash=hash_password("test1234"),
            full_name="Demo KVIC Admin",
            role=UserRole.KVIC_ADMIN,
            is_active=True
        )
        # 2. Beekeeper
        beekeeper_user = User(
            email="test2@gamil.com",
            phone="0987654321",
            password_hash=hash_password("test1234"),
            full_name="Demo Beekeeper",
            role=UserRole.BEEKEEPER,
            is_active=True
        )
        # 3. Buyer
        buyer_user = User(
            email="test3@gamil.com",
            phone="1122334455",
            password_hash=hash_password("test1234"),
            full_name="Demo Buyer",
            role=UserRole.BUYER,
            is_active=True
        )
        db.add_all([kvic_user, beekeeper_user, buyer_user])
        db.commit()
        db.refresh(kvic_user)
        db.refresh(beekeeper_user)
        db.refresh(buyer_user)

        logger.info("Creating Beekeeper Profile...")
        beekeeper_profile = BeekeeperProfile(
            user_id=beekeeper_user.id,
            beekeeper_code="BEE-DEMO",
            address="123 Farm Road, Maharashtra",
            experience_years=8
        )
        db.add(beekeeper_profile)
        db.commit()
        db.refresh(beekeeper_profile)

        logger.info("Creating Apiaries...")
        apiary1 = Apiary(
            beekeeper_id=beekeeper_profile.id,
            name="North Valley Apiary",
            location_name="Nashik, Maharashtra",
            latitude=20.0,
            longitude=73.7
        )
        apiary2 = Apiary(
            beekeeper_id=beekeeper_profile.id,
            name="River Side Apiary",
            location_name="Pune, Maharashtra",
            latitude=18.5,
            longitude=73.8
        )
        db.add_all([apiary1, apiary2])
        db.commit()
        db.refresh(apiary1)
        db.refresh(apiary2)

        logger.info("Creating Hives & IoT States...")
        hives = []
        # Create 3 hives in apiary1
        for i in range(1, 4):
            hive = Hive(
                apiary_id=apiary1.id,
                hive_code=f"NV-HIVE-00{i}",
                hive_type="Langstroth",
                installation_date=datetime.now(timezone.utc) - timedelta(days=30*i),
                status=HiveStatus.ACTIVE
            )
            hives.append(hive)
            db.add(hive)
        
        # Create 2 hives in apiary2
        for i in range(1, 3):
            hive = Hive(
                apiary_id=apiary2.id,
                hive_code=f"RS-HIVE-00{i}",
                hive_type="Top-Bar",
                installation_date=datetime.now(timezone.utc) - timedelta(days=15*i),
                status=HiveStatus.ACTIVE
            )
            hives.append(hive)
            db.add(hive)
        
        db.commit()

        # Generate IoT state for each hive
        for hive in hives:
            iot_state = IoTHiveState(
                hive_id=hive.id,
                temperature=35.0,
                humidity=60.0,
                weight=32.5,
                sound_level=45.0,
                co2_level=600.0,
                activity_level="Normal",
                status="Healthy"
            )
            db.add(iot_state)
        db.commit()

        logger.info("Creating Honey Harvests & Batches...")
        harvest = HoneyHarvest(
            hive_id=hives[0].id,
            harvest_date=datetime.now(timezone.utc) - timedelta(days=5),
            estimated_quantity_kg=20.0,
            actual_quantity_kg=18.5,
            honey_type="Multiflora",
            notes="Spring harvest, rich golden color."
        )
        db.add(harvest)
        db.commit()
        db.refresh(harvest)

        batch = HoneyBatch(
            beekeeper_id=beekeeper_profile.id,
            harvest_id=harvest.id,
            batch_code="BCH-DEMO-001",
            batch_date=datetime.now(timezone.utc).date(),
            honey_type="Multiflora",
            quantity_kg=18.0,
            status=BatchStatus.READY
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        logger.info("Creating Honey Products...")
        product1 = HoneyProduct(
            batch_id=batch.id,
            trace_token="DEMO-TRACE-TOKEN-1",
            serial_number="HC-PRD-0001",
            net_weight_g=500.0,
            packaging_date=datetime.now(timezone.utc),
            status=ProductStatus.ACTIVE,
            qr_code_svg="<svg></svg>", # dummy svg
            price=500.0
        )
        product2 = HoneyProduct(
            batch_id=batch.id,
            trace_token="DEMO-TRACE-TOKEN-2",
            serial_number="HC-PRD-0002",
            net_weight_g=1000.0,
            packaging_date=datetime.now(timezone.utc),
            status=ProductStatus.ACTIVE,
            qr_code_svg="<svg></svg>", # dummy svg
            price=950.0
        )
        db.add_all([product1, product2])
        db.commit()
        db.refresh(product1)

        logger.info("Demo Data Seeding Complete!")

if __name__ == "__main__":
    reset_db()
    seed_data()
