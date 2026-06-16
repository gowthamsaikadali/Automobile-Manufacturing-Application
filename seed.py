import argparse
import random
from datetime import date, timedelta

from app import create_app
from config import Config
from extensions import db
from models import DailyProduction, Inventory, Material, User


app = create_app(Config)


MATERIAL_SEED_DATA = [
    {
        "material_name": "V8 Engine Batch A",
        "material_type": "Engine Block",
        "category": "Engine Components",
        "quantity_produced": 120,
        "quantity_assembled": 110,
        "quantity_delivered": 95,
        "manufacture_date": date.today() - timedelta(days=12),
        "assembly_date": date.today() - timedelta(days=10),
        "delivery_date": date.today() - timedelta(days=6),
        "production_status": "Completed",
        "assembly_status": "Completed",
        "delivery_status": "Delivered",
        "remarks": "Engine batch released for sedan line.",
    },
    {
        "material_name": "SUV Chassis Series 21",
        "material_type": "Chassis Plate",
        "category": "Chassis",
        "quantity_produced": 80,
        "quantity_assembled": 64,
        "quantity_delivered": 40,
        "manufacture_date": date.today() - timedelta(days=9),
        "assembly_date": date.today() - timedelta(days=7),
        "delivery_date": date.today() - timedelta(days=4),
        "production_status": "Completed",
        "assembly_status": "In Progress",
        "delivery_status": "Scheduled",
        "remarks": "Awaiting final inspection for remaining units.",
    },
    {
        "material_name": "Premium Body Shell Lot 7",
        "material_type": "Body Shell",
        "category": "Body Parts",
        "quantity_produced": 150,
        "quantity_assembled": 100,
        "quantity_delivered": 0,
        "manufacture_date": date.today() - timedelta(days=5),
        "assembly_date": date.today() - timedelta(days=3),
        "delivery_date": None,
        "production_status": "Completed",
        "assembly_status": "In Progress",
        "delivery_status": "Pending",
        "remarks": "Paint curing in progress.",
    },
    {
        "material_name": "All-Weather Tire Lot B",
        "material_type": "Tire Set",
        "category": "Tires",
        "quantity_produced": 300,
        "quantity_assembled": 220,
        "quantity_delivered": 200,
        "manufacture_date": date.today() - timedelta(days=8),
        "assembly_date": date.today() - timedelta(days=6),
        "delivery_date": date.today() - timedelta(days=2),
        "production_status": "Completed",
        "assembly_status": "Completed",
        "delivery_status": "Delivered",
        "remarks": "Dispatch completed for truck line.",
    },
    {
        "material_name": "EV Wiring Harness Pack",
        "material_type": "Wiring Harness",
        "category": "Electronics",
        "quantity_produced": 210,
        "quantity_assembled": 160,
        "quantity_delivered": 120,
        "manufacture_date": date.today() - timedelta(days=7),
        "assembly_date": date.today() - timedelta(days=5),
        "delivery_date": date.today() - timedelta(days=1),
        "production_status": "Completed",
        "assembly_status": "Completed",
        "delivery_status": "Scheduled",
        "remarks": "Final delivery truck scheduled tonight.",
    },
    {
        "material_name": "Metallic Paint Kit Series R",
        "material_type": "Paint Kit",
        "category": "Paint Units",
        "quantity_produced": 60,
        "quantity_assembled": 0,
        "quantity_delivered": 0,
        "manufacture_date": date.today() - timedelta(days=2),
        "assembly_date": None,
        "delivery_date": None,
        "production_status": "In Production",
        "assembly_status": "Pending",
        "delivery_status": "Pending",
        "remarks": "Batch under quality test.",
    },
]

INVENTORY_ITEMS = [
    ("Cold Rolled Steel Sheets", "Raw Materials", 500, 240),
    ("Turbo Engine Pistons", "Engine Components", 260, 120),
    ("Radial Tire Sets", "Tires", 420, 180),
    ("Sensor Control Modules", "Electronics", 160, 70),
    ("Chassis Frames", "Chassis", 120, 45),
    ("Body Door Panels", "Body Parts", 210, 90),
    ("Industrial Paint Barrels", "Paint Units", 85, 34),
    ("Interior Accessory Kits", "Accessories", 140, 58),
]

SUPERVISORS = ["Anita Sharma", "Rohit Mehra", "Sanjay Rao", "Priya Nair"]
SHIFTS = ["Morning", "Evening", "Night"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Seed the Automobile Manufacturing Dashboard database."
    )
    parser.add_argument(
        "--admin-only",
        action="store_true",
        help="Create/update only the admin user without inserting sample data.",
    )
    parser.add_argument(
        "--reset-admin-password",
        action="store_true",
        help="Reset the admin password to the value in DEFAULT_ADMIN_PASSWORD.",
    )
    return parser.parse_args()


def seed_database(admin_only: bool = False, reset_admin_password: bool = False):
    with app.app_context():
        db.create_all()

        admin = User.query.filter_by(username=app.config["DEFAULT_ADMIN_USERNAME"]).first()
        if admin is None:
            admin = User(username=app.config["DEFAULT_ADMIN_USERNAME"])
            admin.set_password(app.config["DEFAULT_ADMIN_PASSWORD"])
            db.session.add(admin)
            db.session.commit()
            print(f"Created admin user: {admin.username}")
        else:
            if reset_admin_password:
                admin.set_password(app.config["DEFAULT_ADMIN_PASSWORD"])
                db.session.commit()
                print(f"Reset password for admin user: {admin.username}")
            else:
                print(f"Admin user already exists: {admin.username}")

        if admin_only:
            print("\nAdmin-only seed completed successfully.")
            print(
                f"Admin login -> username: {app.config['DEFAULT_ADMIN_USERNAME']} | "
                f"password: {app.config['DEFAULT_ADMIN_PASSWORD']}"
            )
            return

        if Material.query.count() == 0:
            for row in MATERIAL_SEED_DATA:
                material = Material(created_by_id=admin.id, **row)
                db.session.add(material)
            db.session.commit()
            print("Seeded materials data.")
        else:
            print("Materials already seeded; skipping.")

        if DailyProduction.query.count() == 0:
            for offset in range(14, -1, -1):
                production_date = date.today() - timedelta(days=offset)
                for shift in SHIFTS[:2]:
                    produced = random.randint(40, 120)
                    assembled = random.randint(20, produced)
                    delivered = random.randint(10, assembled)
                    record = DailyProduction(
                        production_date=production_date,
                        produced=produced,
                        assembled=assembled,
                        delivered=delivered,
                        shift=shift,
                        supervisor=random.choice(SUPERVISORS),
                        notes=f"{shift} shift output recorded for {production_date.isoformat()}.",
                        created_by_id=admin.id,
                    )
                    db.session.add(record)
            db.session.commit()
            print("Seeded daily production data.")
        else:
            print("Daily production already seeded; skipping.")

        if Inventory.query.count() == 0:
            for item_name, category, stock, consumed in INVENTORY_ITEMS:
                inventory = Inventory(
                    item_name=item_name,
                    category=category,
                    stock_quantity=stock,
                    consumed_quantity=consumed,
                    remaining_quantity=max(stock - consumed, 0),
                    updated_by_id=admin.id,
                )
                db.session.add(inventory)
            db.session.commit()
            print("Seeded inventory data.")
        else:
            print("Inventory already seeded; skipping.")

        print("\nSeed completed successfully.")
        print(
            f"Admin login -> username: {app.config['DEFAULT_ADMIN_USERNAME']} | "
            f"password: {app.config['DEFAULT_ADMIN_PASSWORD']}"
        )


if __name__ == "__main__":
    args = parse_args()
    seed_database(
        admin_only=args.admin_only,
        reset_admin_password=args.reset_admin_password,
    )
