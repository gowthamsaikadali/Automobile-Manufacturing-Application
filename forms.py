from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, EqualTo, Length, NumberRange, Optional


MATERIAL_TYPE_CHOICES = [
    ("Engine Block", "Engine Block"),
    ("Chassis Plate", "Chassis Plate"),
    ("Body Shell", "Body Shell"),
    ("Tire Set", "Tire Set"),
    ("Wiring Harness", "Wiring Harness"),
    ("Dashboard Console", "Dashboard Console"),
    ("Paint Kit", "Paint Kit"),
    ("Accessory Pack", "Accessory Pack"),
]

CATEGORY_CHOICES = [
    ("Raw Materials", "Raw Materials"),
    ("Engine Components", "Engine Components"),
    ("Tires", "Tires"),
    ("Electronics", "Electronics"),
    ("Chassis", "Chassis"),
    ("Body Parts", "Body Parts"),
    ("Paint Units", "Paint Units"),
    ("Accessories", "Accessories"),
]

PRODUCTION_STATUS_CHOICES = [
    ("Planned", "Planned"),
    ("In Production", "In Production"),
    ("Completed", "Completed"),
    ("On Hold", "On Hold"),
]

ASSEMBLY_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("In Progress", "In Progress"),
    ("Completed", "Completed"),
]

DELIVERY_STATUS_CHOICES = [
    ("Pending", "Pending"),
    ("Scheduled", "Scheduled"),
    ("Delivered", "Delivered"),
]

SHIFT_CHOICES = [
    ("Morning", "Morning"),
    ("Evening", "Evening"),
    ("Night", "Night"),
]

INVENTORY_CATEGORY_CHOICES = CATEGORY_CHOICES


class LoginForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    remember = BooleanField("Remember me")
    submit = SubmitField("Sign In")


class MaterialForm(FlaskForm):
    material_name = StringField("Material Name", validators=[DataRequired(), Length(min=2, max=120)])
    material_type = SelectField("Material Type", choices=MATERIAL_TYPE_CHOICES, validators=[DataRequired()])
    category = SelectField("Category", choices=CATEGORY_CHOICES, validators=[DataRequired()])
    quantity_produced = IntegerField(
        "Quantity Produced",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    quantity_assembled = IntegerField(
        "Quantity Assembled",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    quantity_delivered = IntegerField(
        "Quantity Delivered",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    manufacture_date = DateField(
        "Manufacturing Date",
        validators=[DataRequired()],
        default=date.today,
        format="%Y-%m-%d",
    )
    assembly_date = DateField(
        "Assembly Date",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    delivery_date = DateField(
        "Delivery Date",
        validators=[Optional()],
        format="%Y-%m-%d",
    )
    production_status = SelectField(
        "Production Status",
        choices=PRODUCTION_STATUS_CHOICES,
        validators=[DataRequired()],
        default="Completed",
    )
    assembly_status = SelectField(
        "Assembly Status",
        choices=ASSEMBLY_STATUS_CHOICES,
        validators=[DataRequired()],
        default="Pending",
    )
    delivery_status = SelectField(
        "Delivery Status",
        choices=DELIVERY_STATUS_CHOICES,
        validators=[DataRequired()],
        default="Pending",
    )
    remarks = TextAreaField("Remarks", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save Material")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        if self.quantity_assembled.data > self.quantity_produced.data:
            self.quantity_assembled.errors.append(
                "Assembled quantity cannot exceed produced quantity."
            )
            return False

        if self.quantity_delivered.data > self.quantity_assembled.data:
            self.quantity_delivered.errors.append(
                "Delivered quantity cannot exceed assembled quantity."
            )
            return False

        if self.assembly_date.data and self.assembly_date.data < self.manufacture_date.data:
            self.assembly_date.errors.append(
                "Assembly date cannot be earlier than manufacturing date."
            )
            return False

        if self.delivery_date.data and self.delivery_date.data < self.manufacture_date.data:
            self.delivery_date.errors.append(
                "Delivery date cannot be earlier than manufacturing date."
            )
            return False

        if self.delivery_date.data and self.assembly_date.data and self.delivery_date.data < self.assembly_date.data:
            self.delivery_date.errors.append(
                "Delivery date cannot be earlier than assembly date."
            )
            return False

        if self.assembly_status.data == "Completed" and not self.assembly_date.data:
            self.assembly_date.errors.append(
                "Assembly date is required when assembly status is completed."
            )
            return False

        if self.delivery_status.data == "Delivered" and not self.delivery_date.data:
            self.delivery_date.errors.append(
                "Delivery date is required when delivery status is delivered."
            )
            return False

        return True


class DailyProductionForm(FlaskForm):
    production_date = DateField(
        "Date",
        validators=[DataRequired()],
        default=date.today,
        format="%Y-%m-%d",
    )
    produced = IntegerField("Total Produced", validators=[DataRequired(), NumberRange(min=0)], default=0)
    assembled = IntegerField(
        "Total Assembled",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    delivered = IntegerField(
        "Total Delivered",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    shift = SelectField("Shift", choices=SHIFT_CHOICES, validators=[DataRequired()])
    supervisor = StringField("Supervisor Name", validators=[DataRequired(), Length(min=2, max=120)])
    notes = TextAreaField("Notes", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Save Production Record")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        if self.assembled.data > self.produced.data:
            self.assembled.errors.append("Assembled quantity cannot exceed produced quantity.")
            return False

        if self.delivered.data > self.assembled.data:
            self.delivered.errors.append("Delivered quantity cannot exceed assembled quantity.")
            return False

        return True


class InventoryForm(FlaskForm):
    item_name = StringField("Item Name", validators=[DataRequired(), Length(min=2, max=120)])
    category = SelectField("Category", choices=INVENTORY_CATEGORY_CHOICES, validators=[DataRequired()])
    stock_quantity = IntegerField(
        "Current Stock",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    consumed_quantity = IntegerField(
        "Consumed Quantity",
        validators=[DataRequired(), NumberRange(min=0)],
        default=0,
    )
    submit = SubmitField("Save Inventory")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators=extra_validators):
            return False

        if self.consumed_quantity.data > self.stock_quantity.data:
            self.consumed_quantity.errors.append(
                "Consumed quantity cannot exceed current stock quantity."
            )
            return False

        return True


class ProfileForm(FlaskForm):
    username = StringField("Username", validators=[DataRequired(), Length(min=3, max=80)])
    current_password = PasswordField(
        "Current Password",
        validators=[DataRequired(), Length(min=6, max=128)],
    )
    new_password = PasswordField(
        "New Password",
        validators=[Optional(), Length(min=6, max=128)],
    )
    confirm_new_password = PasswordField(
        "Confirm New Password",
        validators=[Optional(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Update Profile")
