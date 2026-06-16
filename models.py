from datetime import date, datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    materials = db.relationship("Material", back_populates="created_by", lazy=True)
    production_logs = db.relationship("DailyProduction", back_populates="created_by", lazy=True)
    inventory_updates = db.relationship("Inventory", back_populates="updated_by", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


class Material(TimestampMixin, db.Model):
    __tablename__ = "materials"

    id = db.Column(db.Integer, primary_key=True)
    material_name = db.Column(db.String(120), nullable=False, index=True)
    material_type = db.Column(db.String(80), nullable=False, index=True)
    category = db.Column(db.String(80), nullable=False, index=True)
    quantity_produced = db.Column(db.Integer, nullable=False, default=0)
    quantity_assembled = db.Column(db.Integer, nullable=False, default=0)
    quantity_delivered = db.Column(db.Integer, nullable=False, default=0)
    manufacture_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    assembly_date = db.Column(db.Date, nullable=True)
    delivery_date = db.Column(db.Date, nullable=True)
    production_status = db.Column(db.String(30), nullable=False, default="Completed", index=True)
    assembly_status = db.Column(db.String(30), nullable=False, default="Pending", index=True)
    delivery_status = db.Column(db.String(30), nullable=False, default="Pending", index=True)
    remarks = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_by = db.relationship("User", back_populates="materials")

    __table_args__ = (
        db.CheckConstraint("quantity_produced >= 0", name="ck_materials_qty_produced_non_negative"),
        db.CheckConstraint("quantity_assembled >= 0", name="ck_materials_qty_assembled_non_negative"),
        db.CheckConstraint("quantity_delivered >= 0", name="ck_materials_qty_delivered_non_negative"),
        db.CheckConstraint(
            "quantity_assembled <= quantity_produced",
            name="ck_materials_assembled_lte_produced",
        ),
        db.CheckConstraint(
            "quantity_delivered <= quantity_assembled",
            name="ck_materials_delivered_lte_assembled",
        ),
    )

    @property
    def pending_assembly(self) -> int:
        return max(self.quantity_produced - self.quantity_assembled, 0)

    @property
    def pending_delivery(self) -> int:
        return max(self.quantity_assembled - self.quantity_delivered, 0)

    def __repr__(self) -> str:
        return f"<Material {self.material_name}>"


class DailyProduction(TimestampMixin, db.Model):
    __tablename__ = "daily_production"

    id = db.Column(db.Integer, primary_key=True)
    production_date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    produced = db.Column(db.Integer, nullable=False, default=0)
    assembled = db.Column(db.Integer, nullable=False, default=0)
    delivered = db.Column(db.Integer, nullable=False, default=0)
    shift = db.Column(db.String(20), nullable=False, default="Morning")
    supervisor = db.Column(db.String(120), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    created_by = db.relationship("User", back_populates="production_logs")

    __table_args__ = (
        db.UniqueConstraint("production_date", "shift", name="uq_daily_production_date_shift"),
        db.CheckConstraint("produced >= 0", name="ck_daily_production_produced_non_negative"),
        db.CheckConstraint("assembled >= 0", name="ck_daily_production_assembled_non_negative"),
        db.CheckConstraint("delivered >= 0", name="ck_daily_production_delivered_non_negative"),
        db.CheckConstraint("assembled <= produced", name="ck_daily_production_assembled_lte_produced"),
        db.CheckConstraint("delivered <= assembled", name="ck_daily_production_delivered_lte_assembled"),
    )

    def __repr__(self) -> str:
        return f"<DailyProduction {self.production_date} {self.shift}>"


class Inventory(TimestampMixin, db.Model):
    __tablename__ = "inventory"

    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(120), nullable=False, unique=True, index=True)
    category = db.Column(db.String(80), nullable=False, index=True)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    consumed_quantity = db.Column(db.Integer, nullable=False, default=0)
    remaining_quantity = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )
    updated_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    updated_by = db.relationship("User", back_populates="inventory_updates")

    __table_args__ = (
        db.CheckConstraint("stock_quantity >= 0", name="ck_inventory_stock_non_negative"),
        db.CheckConstraint("consumed_quantity >= 0", name="ck_inventory_consumed_non_negative"),
        db.CheckConstraint("remaining_quantity >= 0", name="ck_inventory_remaining_non_negative"),
        db.CheckConstraint("consumed_quantity <= stock_quantity", name="ck_inventory_consumed_lte_stock"),
    )

    def recalculate_remaining(self) -> None:
        self.remaining_quantity = max(self.stock_quantity - self.consumed_quantity, 0)

    def __repr__(self) -> str:
        return f"<Inventory {self.item_name}>"
