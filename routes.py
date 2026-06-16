import csv
import logging
from collections import defaultdict
from datetime import date, datetime, timedelta
from io import StringIO
from urllib.parse import urljoin, urlparse

from flask import Blueprint, Response, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import String, cast, func, or_, text

from extensions import db
from forms import (
    ASSEMBLY_STATUS_CHOICES,
    DELIVERY_STATUS_CHOICES,
    MATERIAL_TYPE_CHOICES,
    PRODUCTION_STATUS_CHOICES,
    DailyProductionForm,
    InventoryForm,
    LoginForm,
    MaterialForm,
    ProfileForm,
)
from models import DailyProduction, Inventory, Material, User


main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


BADGE_MAP = {
    "Completed": "success",
    "Delivered": "success",
    "In Production": "primary",
    "In Progress": "primary",
    "Scheduled": "info",
    "Pending": "warning",
    "Planned": "secondary",
    "On Hold": "danger",
}


@main_bp.app_context_processor
def inject_helpers():
    return {
        "badge_class": lambda value: BADGE_MAP.get(value, "secondary"),
        "app_name": current_app.config.get("APP_NAME", "Automobile Manufacturing Dashboard"),
    }


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))


@main_bp.route("/health", methods=["GET"])
def health():
    healthcheck_token = current_app.config.get("HEALTHCHECK_TOKEN")
    provided_token = request.headers.get("X-Health-Token")

    if healthcheck_token and provided_token != healthcheck_token:
        return {"status": "forbidden"}, 403

    try:
        db.session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "database": "up",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }, 200
    except Exception as exc:
        logger.exception("Health check failed: %s", exc)
        return {
            "status": "degraded",
            "database": "down",
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }, 503


@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            logger.info("User '%s' logged in successfully.", username)
            flash("Login successful. Welcome back.", "success")
            next_url = request.args.get("next")
            if next_url and _is_safe_url(next_url):
                return redirect(next_url)
            return redirect(url_for("main.dashboard"))

        logger.warning(
            "Failed login attempt for username '%s' from %s.",
            username,
            request.headers.get("X-Forwarded-For", request.remote_addr),
        )
        flash("Invalid username or password.", "danger")

    return render_template("login.html", form=form, title="Login")


@main_bp.route("/logout", methods=["POST"])
@login_required
def logout():
    username = current_user.username
    logout_user()
    logger.info("User '%s' logged out.", username)
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("main.login"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)

    total_produced = db.session.query(func.coalesce(func.sum(Material.quantity_produced), 0)).scalar()
    total_assembled = db.session.query(func.coalesce(func.sum(Material.quantity_assembled), 0)).scalar()
    total_delivered = db.session.query(func.coalesce(func.sum(Material.quantity_delivered), 0)).scalar()
    pending_assembly_count = Material.query.filter(Material.assembly_status != "Completed").count()
    pending_delivery_count = Material.query.filter(Material.delivery_status != "Delivered").count()
    total_material_types = db.session.query(func.count(func.distinct(Material.material_type))).scalar()
    daily_production_count = (
        db.session.query(func.coalesce(func.sum(DailyProduction.produced), 0))
        .filter(DailyProduction.production_date == today)
        .scalar()
    )
    monthly_production_count = (
        db.session.query(func.coalesce(func.sum(DailyProduction.produced), 0))
        .filter(DailyProduction.production_date >= month_start)
        .scalar()
    )

    production_records = (
        DailyProduction.query.filter(DailyProduction.production_date >= today - timedelta(days=31))
        .order_by(DailyProduction.production_date.asc())
        .all()
    )
    production_map = defaultdict(lambda: {"produced": 0, "assembled": 0, "delivered": 0})
    for record in production_records:
        production_map[record.production_date]["produced"] += record.produced
        production_map[record.production_date]["assembled"] += record.assembled
        production_map[record.production_date]["delivered"] += record.delivered

    trend_labels = []
    trend_values = []
    history_labels = []
    history_produced = []
    history_assembled = []
    history_delivered = []

    for offset in range(6, -1, -1):
        trend_date = today - timedelta(days=offset)
        trend_labels.append(trend_date.strftime("%d %b"))
        trend_values.append(production_map[trend_date]["produced"])

    for offset in range(11, -1, -1):
        history_date = today - timedelta(days=offset)
        history_labels.append(history_date.strftime("%d %b"))
        history_produced.append(production_map[history_date]["produced"])
        history_assembled.append(production_map[history_date]["assembled"])
        history_delivered.append(production_map[history_date]["delivered"])

    type_rows = (
        db.session.query(
            Material.material_type,
            func.count(Material.id),
            func.coalesce(func.sum(Material.quantity_produced), 0),
        )
        .group_by(Material.material_type)
        .order_by(Material.material_type.asc())
        .all()
    )
    type_labels = [row[0] for row in type_rows]
    type_counts = [row[1] for row in type_rows]
    type_quantities = [row[2] for row in type_rows]

    recent_materials = (
        Material.query.order_by(Material.manufacture_date.desc(), Material.id.desc()).limit(8).all()
    )
    low_inventory_items = (
        Inventory.query.order_by(Inventory.remaining_quantity.asc(), Inventory.item_name.asc()).limit(8).all()
    )

    dashboard_data = {
        "kpis": {
            "total_produced": total_produced,
            "total_assembled": total_assembled,
            "total_delivered": total_delivered,
            "pending_assembly_count": pending_assembly_count,
            "pending_delivery_count": pending_delivery_count,
            "total_material_types": total_material_types,
            "daily_production_count": daily_production_count,
            "monthly_production_count": monthly_production_count,
        },
        "charts": {
            "daily_trend": {"labels": trend_labels, "values": trend_values},
            "delivered_vs_assembled": {
                "labels": ["Assembled", "Delivered"],
                "values": [total_assembled, total_delivered],
            },
            "material_distribution": {
                "labels": type_labels,
                "counts": type_counts,
                "quantities": type_quantities,
            },
            "production_history": {
                "labels": history_labels,
                "produced": history_produced,
                "assembled": history_assembled,
                "delivered": history_delivered,
            },
        },
    }

    return render_template(
        "dashboard.html",
        title="Dashboard",
        dashboard_data=dashboard_data,
        recent_materials=recent_materials,
        low_inventory_items=low_inventory_items,
    )


@main_bp.route("/materials")
@login_required
def materials():
    search_term = request.args.get("q", "").strip()
    material_type = request.args.get("material_type", "").strip()
    production_status = request.args.get("production_status", "").strip()
    delivery_status = request.args.get("delivery_status", "").strip()

    query = Material.query

    if search_term:
        query = query.filter(
            or_(
                Material.material_name.ilike(f"%{search_term}%"),
                Material.category.ilike(f"%{search_term}%"),
                Material.material_type.ilike(f"%{search_term}%"),
                cast(Material.id, String).ilike(f"%{search_term}%"),
            )
        )

    if material_type:
        query = query.filter(Material.material_type == material_type)

    if production_status:
        query = query.filter(Material.production_status == production_status)

    if delivery_status:
        query = query.filter(Material.delivery_status == delivery_status)

    materials_list = query.order_by(Material.manufacture_date.desc(), Material.id.desc()).all()

    return render_template(
        "materials.html",
        title="Materials",
        materials=materials_list,
        search_term=search_term,
        selected_type=material_type,
        selected_production_status=production_status,
        selected_delivery_status=delivery_status,
        material_type_choices=MATERIAL_TYPE_CHOICES,
        production_status_choices=PRODUCTION_STATUS_CHOICES,
        delivery_status_choices=DELIVERY_STATUS_CHOICES,
    )


@main_bp.route("/materials/add", methods=["GET", "POST"])
@login_required
def add_material():
    form = MaterialForm()
    if form.validate_on_submit():
        material = Material(created_by_id=current_user.id)
        _populate_material_from_form(material, form)

        try:
            db.session.add(material)
            db.session.commit()
            flash("Material added successfully.", "success")
            return redirect(url_for("main.materials"))
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unable to add material: %s", exc)
            flash("Unable to add material. Please try again.", "danger")

    return render_template("add_material.html", title="Add Material", form=form)


@main_bp.route("/materials/<int:material_id>/edit", methods=["GET", "POST"])
@login_required
def edit_material(material_id):
    material = Material.query.get_or_404(material_id)
    form = MaterialForm(obj=material)

    if form.validate_on_submit():
        _populate_material_from_form(material, form)
        try:
            db.session.commit()
            flash("Material updated successfully.", "success")
            return redirect(url_for("main.materials"))
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unable to update material %s: %s", material_id, exc)
            flash("Unable to update material. Please try again.", "danger")

    return render_template("edit_material.html", title="Edit Material", form=form, material=material)


@main_bp.route("/materials/<int:material_id>/delete", methods=["POST"])
@login_required
def delete_material(material_id):
    material = Material.query.get_or_404(material_id)
    try:
        db.session.delete(material)
        db.session.commit()
        flash("Material deleted successfully.", "info")
    except Exception as exc:
        db.session.rollback()
        logger.exception("Unable to delete material %s: %s", material_id, exc)
        flash("Unable to delete material. Please try again.", "danger")
    return redirect(url_for("main.materials"))


@main_bp.route("/production", methods=["GET", "POST"])
@login_required
def production():
    form = DailyProductionForm()

    if form.validate_on_submit():
        record = DailyProduction.query.filter_by(
            production_date=form.production_date.data,
            shift=form.shift.data,
        ).first()

        action = "updated" if record else "created"
        if record is None:
            record = DailyProduction(created_by_id=current_user.id)
            db.session.add(record)

        record.production_date = form.production_date.data
        record.produced = form.produced.data
        record.assembled = form.assembled.data
        record.delivered = form.delivered.data
        record.shift = form.shift.data
        record.supervisor = form.supervisor.data.strip()
        record.notes = form.notes.data.strip() if form.notes.data else None
        record.created_by_id = current_user.id

        try:
            db.session.commit()
            flash(f"Production record {action} successfully.", "success")
            return redirect(url_for("main.production"))
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unable to save production record for %s %s: %s", form.production_date.data, form.shift.data, exc)
            flash("Unable to save production record. Please try again.", "danger")

    records = DailyProduction.query.order_by(
        DailyProduction.production_date.desc(), DailyProduction.shift.asc()
    ).all()

    summary = {
        "records_count": len(records),
        "produced": sum(record.produced for record in records),
        "assembled": sum(record.assembled for record in records),
        "delivered": sum(record.delivered for record in records),
    }

    return render_template(
        "production.html",
        title="Production Tracking",
        form=form,
        records=records,
        summary=summary,
    )


@main_bp.route("/inventory", methods=["GET", "POST"])
@login_required
def inventory():
    edit_id = request.args.get("edit", type=int)
    editing_item = Inventory.query.get(edit_id) if edit_id else None

    if editing_item and request.method == "GET":
        form = InventoryForm(obj=editing_item)
    else:
        form = InventoryForm()

    if form.validate_on_submit():
        inventory_id = request.form.get("inventory_id", type=int)
        item = Inventory.query.get_or_404(inventory_id) if inventory_id else Inventory()

        item.item_name = form.item_name.data.strip()
        item.category = form.category.data
        item.stock_quantity = form.stock_quantity.data
        item.consumed_quantity = form.consumed_quantity.data
        item.recalculate_remaining()
        item.updated_by_id = current_user.id

        try:
            db.session.add(item)
            db.session.commit()
            flash("Inventory saved successfully.", "success")
            return redirect(url_for("main.inventory"))
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unable to save inventory item '%s': %s", item.item_name, exc)
            flash("Unable to save inventory item. Please ensure the item name is unique.", "danger")
            if inventory_id:
                editing_item = item

    inventory_items = Inventory.query.order_by(Inventory.category.asc(), Inventory.item_name.asc()).all()
    summary = {
        "stock": sum(item.stock_quantity for item in inventory_items),
        "consumed": sum(item.consumed_quantity for item in inventory_items),
        "remaining": sum(item.remaining_quantity for item in inventory_items),
        "low_stock_count": sum(1 for item in inventory_items if item.remaining_quantity < 50),
    }

    return render_template(
        "inventory.html",
        title="Inventory",
        form=form,
        inventory_items=inventory_items,
        summary=summary,
        editing_item=editing_item,
    )


@main_bp.route("/inventory/<int:item_id>/delete", methods=["POST"])
@login_required
def delete_inventory(item_id):
    item = Inventory.query.get_or_404(item_id)
    try:
        db.session.delete(item)
        db.session.commit()
        flash("Inventory item deleted successfully.", "info")
    except Exception as exc:
        db.session.rollback()
        logger.exception("Unable to delete inventory item %s: %s", item_id, exc)
        flash("Unable to delete inventory item. Please try again.", "danger")
    return redirect(url_for("main.inventory"))


@main_bp.route("/reports")
@login_required
def reports():
    start_date, end_date = _get_report_date_range()
    report_data = _build_report_data(start_date, end_date)

    return render_template(
        "reports.html",
        title="Reports",
        start_date=start_date,
        end_date=end_date,
        report_data=report_data,
    )


@main_bp.route("/reports/export/<string:report_type>")
@login_required
def export_report(report_type):
    start_date, end_date = _get_report_date_range()
    report_data = _build_report_data(start_date, end_date)

    output = StringIO()
    writer = csv.writer(output)
    filename = f"{report_type}-report-{start_date.isoformat()}-to-{end_date.isoformat()}.csv"

    if report_type == "daily":
        writer.writerow(["Date", "Shift", "Produced", "Assembled", "Delivered", "Supervisor", "Notes"])
        for record in report_data["daily_records"]:
            writer.writerow(
                [
                    record.production_date.isoformat(),
                    record.shift,
                    record.produced,
                    record.assembled,
                    record.delivered,
                    record.supervisor,
                    record.notes or "",
                ]
            )
    elif report_type == "weekly":
        writer.writerow(["Week", "Produced", "Assembled", "Delivered"])
        for row in report_data["weekly_summary"]:
            writer.writerow([row["week"], row["produced"], row["assembled"], row["delivered"]])
    elif report_type == "monthly":
        writer.writerow(["Month", "Produced", "Assembled", "Delivered"])
        for row in report_data["monthly_summary"]:
            writer.writerow([row["month"], row["produced"], row["assembled"], row["delivered"]])
    elif report_type == "delivered":
        writer.writerow(["Material Type", "Materials Delivered", "Quantity Delivered"])
        for row in report_data["delivered_report"]:
            writer.writerow([row["material_type"], row["materials"], row["quantity"]])
    elif report_type == "assembly":
        writer.writerow(["Assembly Status", "Materials", "Quantity Assembled"])
        for row in report_data["assembly_report"]:
            writer.writerow([row["status"], row["materials"], row["assembled"]])
    elif report_type in {"material-type", "material_type"}:
        writer.writerow(
            [
                "Material Type",
                "Material Count",
                "Quantity Produced",
                "Quantity Assembled",
                "Quantity Delivered",
            ]
        )
        for row in report_data["material_type_report"]:
            writer.writerow(
                [
                    row["material_type"],
                    row["count"],
                    row["produced"],
                    row["assembled"],
                    row["delivered"],
                ]
            )
    else:
        flash("Unknown report type requested.", "warning")
        return redirect(url_for("main.reports"))

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    form = ProfileForm()

    if request.method == "GET":
        form.username.data = current_user.username

    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            flash("Current password is incorrect.", "danger")
            return render_template("profile.html", title="Profile", form=form)

        duplicate_user = User.query.filter(
            User.username == form.username.data.strip(), User.id != current_user.id
        ).first()
        if duplicate_user:
            flash("Username already exists. Please choose another one.", "warning")
            return render_template("profile.html", title="Profile", form=form)

        current_user.username = form.username.data.strip()
        if form.new_password.data:
            current_user.set_password(form.new_password.data)

        try:
            db.session.commit()
            flash("Profile updated successfully.", "success")
            return redirect(url_for("main.profile"))
        except Exception as exc:
            db.session.rollback()
            logger.exception("Unable to update profile for user %s: %s", current_user.id, exc)
            flash("Unable to update profile. Please try again.", "danger")

    return render_template("profile.html", title="Profile", form=form)


def _is_safe_url(target: str) -> bool:
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in {"http", "https"} and ref_url.netloc == test_url.netloc


def _populate_material_from_form(material: Material, form: MaterialForm) -> None:
    material.material_name = form.material_name.data.strip()
    material.material_type = form.material_type.data
    material.category = form.category.data
    material.quantity_produced = form.quantity_produced.data
    material.quantity_assembled = form.quantity_assembled.data
    material.quantity_delivered = form.quantity_delivered.data
    material.manufacture_date = form.manufacture_date.data
    material.assembly_date = form.assembly_date.data
    material.delivery_date = form.delivery_date.data
    material.production_status = form.production_status.data
    material.assembly_status = form.assembly_status.data
    material.delivery_status = form.delivery_status.data
    material.remarks = form.remarks.data.strip() if form.remarks.data else None


def _parse_date(value: str | None, default: date) -> date:
    if not value:
        return default
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return default


def _get_report_date_range() -> tuple[date, date]:
    end_date = _parse_date(request.args.get("end_date"), date.today())
    start_date = _parse_date(request.args.get("start_date"), end_date - timedelta(days=30))
    if start_date > end_date:
        start_date, end_date = end_date, start_date
    return start_date, end_date


def _build_report_data(start_date: date, end_date: date) -> dict:
    daily_records = (
        DailyProduction.query.filter(DailyProduction.production_date.between(start_date, end_date))
        .order_by(DailyProduction.production_date.asc(), DailyProduction.shift.asc())
        .all()
    )
    materials_in_range = (
        Material.query.filter(Material.manufacture_date.between(start_date, end_date))
        .order_by(Material.manufacture_date.asc(), Material.id.asc())
        .all()
    )
    delivered_materials = [
        material
        for material in materials_in_range
        if material.delivery_status == "Delivered" or material.quantity_delivered > 0
    ]

    summary = {
        "produced": sum(record.produced for record in daily_records),
        "assembled": sum(record.assembled for record in daily_records),
        "delivered": sum(record.delivered for record in daily_records),
        "records_count": len(daily_records),
        "materials_count": len(materials_in_range),
    }

    weekly_bucket = defaultdict(lambda: {"produced": 0, "assembled": 0, "delivered": 0})
    monthly_bucket = defaultdict(lambda: {"produced": 0, "assembled": 0, "delivered": 0})
    for record in daily_records:
        iso_year, iso_week, _ = record.production_date.isocalendar()
        week_key = f"{iso_year}-W{iso_week:02d}"
        month_key = record.production_date.strftime("%Y-%m")

        weekly_bucket[week_key]["produced"] += record.produced
        weekly_bucket[week_key]["assembled"] += record.assembled
        weekly_bucket[week_key]["delivered"] += record.delivered

        monthly_bucket[month_key]["produced"] += record.produced
        monthly_bucket[month_key]["assembled"] += record.assembled
        monthly_bucket[month_key]["delivered"] += record.delivered

    material_type_bucket = defaultdict(
        lambda: {"count": 0, "produced": 0, "assembled": 0, "delivered": 0}
    )
    assembly_bucket = defaultdict(lambda: {"materials": 0, "assembled": 0})
    delivered_bucket = defaultdict(lambda: {"materials": 0, "quantity": 0})

    for material in materials_in_range:
        material_type_bucket[material.material_type]["count"] += 1
        material_type_bucket[material.material_type]["produced"] += material.quantity_produced
        material_type_bucket[material.material_type]["assembled"] += material.quantity_assembled
        material_type_bucket[material.material_type]["delivered"] += material.quantity_delivered

        assembly_bucket[material.assembly_status]["materials"] += 1
        assembly_bucket[material.assembly_status]["assembled"] += material.quantity_assembled

    for material in delivered_materials:
        delivered_bucket[material.material_type]["materials"] += 1
        delivered_bucket[material.material_type]["quantity"] += material.quantity_delivered

    weekly_summary = [
        {
            "week": key,
            "produced": value["produced"],
            "assembled": value["assembled"],
            "delivered": value["delivered"],
        }
        for key, value in sorted(weekly_bucket.items())
    ]
    monthly_summary = [
        {
            "month": key,
            "produced": value["produced"],
            "assembled": value["assembled"],
            "delivered": value["delivered"],
        }
        for key, value in sorted(monthly_bucket.items())
    ]
    material_type_report = [
        {
            "material_type": key,
            "count": value["count"],
            "produced": value["produced"],
            "assembled": value["assembled"],
            "delivered": value["delivered"],
        }
        for key, value in sorted(material_type_bucket.items())
    ]
    assembly_report = [
        {
            "status": key,
            "materials": value["materials"],
            "assembled": value["assembled"],
        }
        for key, value in sorted(assembly_bucket.items())
    ]
    delivered_report = [
        {
            "material_type": key,
            "materials": value["materials"],
            "quantity": value["quantity"],
        }
        for key, value in sorted(delivered_bucket.items())
    ]

    return {
        "summary": summary,
        "daily_records": daily_records,
        "weekly_summary": weekly_summary,
        "monthly_summary": monthly_summary,
        "material_type_report": material_type_report,
        "assembly_report": assembly_report,
        "delivered_report": delivered_report,
    }
