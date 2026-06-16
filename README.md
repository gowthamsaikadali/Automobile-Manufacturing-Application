# Automobile Manufacturing Dashboard

A production-ready two-tier web application built with Flask, SQLAlchemy, and AWS deployment best practices for an Automobile Manufacturing Unit.

## Architecture

- **Tier 1:** Python Flask application on **AWS EC2**
- **Tier 2:** **AWS RDS** (PostgreSQL or MySQL) in a **private subnet**
- **Web Server:** Nginx
- **Application Server:** Gunicorn
- **ORM:** SQLAlchemy
- **Migrations:** Flask-Migrate
- **Authentication:** Flask-Login with hashed passwords

## Features

### Dashboard
- Total Materials Produced
- Total Materials Assembled
- Total Materials Delivered
- Pending Assembly Count
- Pending Delivery Count
- Total Material Types
- Daily Production Count
- Monthly Production Count
- Charts for daily trend, delivered vs assembled, material distribution, and production history

### Material Management
- Add, edit, delete, and list materials
- Search by ID, name, type, or category
- Filter by material type, production status, and delivery status

### Daily Production Tracking
- Maintain date-wise production logs
- Track shift, supervisor, notes, produced, assembled, delivered
- Auto summary totals on page and reports

### Inventory Module
- Track raw materials, engine components, tires, electronics, chassis, body parts, paint units, and accessories
- Track current stock, consumed quantity, remaining quantity, last updated

### Reports
- Daily production report
- Weekly report
- Monthly report
- Delivered report
- Assembly report
- Material type report
- CSV export support

### Security and Production Readiness
- Password hashing with Werkzeug
- CSRF protection via Flask-WTF
- Session-based authentication
- SQLAlchemy ORM to avoid raw SQL injection risks
- Environment-based configuration
- Nginx + Gunicorn deployment configuration included

## Project Structure

```text
automobile-manufacturing-app/
├── app.py
├── wsgi.py
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── models.py
├── forms.py
├── routes.py
├── extensions.py
├── seed.py
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── materials.html
│   ├── add_material.html
│   ├── edit_material.html
│   ├── inventory.html
│   ├── production.html
│   ├── reports.html
│   ├── profile.html
│   └── error.html
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── app.js
│   └── images/
├── deploy/
│   ├── gunicorn.service
│   └── nginx.conf
└── migrations/
    └── README.md
```

## Database Models

### users
- id
- username
- password_hash
- created_at
- updated_at

### materials
- id
- material_name
- material_type
- category
- quantity_produced
- quantity_assembled
- quantity_delivered
- manufacture_date
- assembly_date
- delivery_date
- production_status
- assembly_status
- delivery_status
- remarks
- created_by_id
- created_at
- updated_at

### daily_production
- id
- production_date
- produced
- assembled
- delivered
- shift
- supervisor
- notes
- created_by_id
- created_at
- updated_at

### inventory
- id
- item_name
- category
- stock_quantity
- consumed_quantity
- remaining_quantity
- last_updated
- updated_by_id
- created_at
- updated_at

## Local Development Setup

### 1. Create and activate a virtual environment

```bash
cd automobile-manufacturing-app
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Update `.env` with your preferred database URI.

#### PostgreSQL example
```env
DATABASE_URL=postgresql+psycopg2://postgres:StrongPassword@localhost:5432/automobile_manufacturing
```

#### MySQL example
```env
DATABASE_URL=mysql+pymysql://root:StrongPassword@localhost:3306/automobile_manufacturing
```

### 4. Create the database

#### PostgreSQL
```bash
sudo -u postgres psql
CREATE DATABASE automobile_manufacturing;
CREATE USER app_user WITH PASSWORD 'StrongPassword';
GRANT ALL PRIVILEGES ON DATABASE automobile_manufacturing TO app_user;
\q
```

#### MySQL
```bash
mysql -u root -p
CREATE DATABASE automobile_manufacturing CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'app_user'@'localhost' IDENTIFIED BY 'StrongPassword';
GRANT ALL PRIVILEGES ON automobile_manufacturing.* TO 'app_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 5. Run migrations

```bash
export FLASK_APP=app.py
flask db init        # only first time if migrations are not yet initialized
flask db migrate -m "Initial schema"
flask db upgrade
```

### 6. Seed sample data

```bash
python seed.py
```

Default admin credentials after seeding:

```text
username: admin
password: Admin@123
```

You can change these using `DEFAULT_ADMIN_USERNAME` and `DEFAULT_ADMIN_PASSWORD` in `.env`.

### 7. Start the application locally

```bash
flask run --host 0.0.0.0 --port 5000
```

Open:

```text
http://127.0.0.1:5000
```

## Production Deployment on AWS EC2 + RDS

## Recommended AWS Design

### VPC Layout
- **Public subnet:** EC2 instance (Nginx + Gunicorn + Flask)
- **Private subnet:** RDS PostgreSQL or MySQL
- **Internet Gateway:** attached to VPC
- **Route Tables:** public subnet routed to IGW, private DB subnet isolated

### Security Groups

#### EC2 Security Group
Allow:
- TCP 22 from your trusted admin IP
- TCP 80 from internet
- TCP 443 from internet

#### RDS Security Group
Allow:
- PostgreSQL 5432 **or** MySQL 3306
- **Source:** EC2 security group only

This ensures the RDS instance is not publicly accessible and only the EC2 application can reach it.

## EC2 Setup Example (Amazon Linux / Ubuntu style flow)

### 1. Connect to EC2

```bash
ssh -i your-key.pem ec2-user@your-ec2-public-ip
```

### 2. Install system packages

For Amazon Linux 2023:

```bash
sudo dnf update -y
sudo dnf install -y git nginx python3 python3-pip python3-devel gcc
```

For Ubuntu:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git nginx python3 python3-pip python3-venv python3-dev build-essential libpq-dev
```

### 3. Copy application to EC2

```bash
sudo mkdir -p /opt/automobile-manufacturing-app
sudo chown $USER:$USER /opt/automobile-manufacturing-app
cd /opt/automobile-manufacturing-app
# then copy files here using git clone or scp
```

### 4. Create venv and install dependencies

```bash
cd /opt/automobile-manufacturing-app
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure environment

```bash
cp .env.example .env
nano .env
```

Example for AWS RDS PostgreSQL:

```env
FLASK_ENV=production
FLASK_DEBUG=false
SECRET_KEY=replace-with-a-random-value
SESSION_COOKIE_SECURE=true
DATABASE_URL=postgresql+psycopg2://app_user:StrongPassword@your-rds-endpoint.region.rds.amazonaws.com:5432/automobile_manufacturing
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=Admin@123
```

Example for AWS RDS MySQL:

```env
DATABASE_URL=mysql+pymysql://app_user:StrongPassword@your-rds-endpoint.region.rds.amazonaws.com:3306/automobile_manufacturing
```

### 6. Run schema migration and seed data

```bash
source /opt/automobile-manufacturing-app/.venv/bin/activate
cd /opt/automobile-manufacturing-app
export FLASK_APP=app.py
flask db init        # only first time if repo does not contain generated migrations
flask db migrate -m "Initial schema"
flask db upgrade
python seed.py
```

## Gunicorn Setup

Copy the included systemd file and adjust `User`/`Group` if required.

```bash
sudo cp deploy/gunicorn.service /etc/systemd/system/automobile-manufacturing-app.service
sudo systemctl daemon-reload
sudo systemctl enable automobile-manufacturing-app.service
sudo systemctl start automobile-manufacturing-app.service
sudo systemctl status automobile-manufacturing-app.service
```

## Nginx Setup

```bash
sudo cp deploy/nginx.conf /etc/nginx/conf.d/automobile-manufacturing-app.conf
sudo nginx -t
sudo systemctl enable nginx
sudo systemctl restart nginx
```

If using Ubuntu and the default site is enabled, disable it:

```bash
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx
```

## Optional HTTPS with Let's Encrypt

For production, terminate TLS at Nginx:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain-name
```

## Operational Commands

### Restart Gunicorn
```bash
sudo systemctl restart automobile-manufacturing-app.service
```

### Restart Nginx
```bash
sudo systemctl restart nginx
```

### View Gunicorn logs
```bash
sudo journalctl -u automobile-manufacturing-app.service -f
```

### Test RDS connectivity from EC2

#### PostgreSQL
```bash
psql "host=your-rds-endpoint user=app_user dbname=automobile_manufacturing password=StrongPassword"
```

#### MySQL
```bash
mysql -h your-rds-endpoint -u app_user -p automobile_manufacturing
```

## Notes

- The app supports both PostgreSQL and MySQL through SQLAlchemy connection strings.
- For local development, if no `DATABASE_URL` is provided, the app falls back to SQLite.
- Chart.js and Bootstrap are loaded from CDN for production browser use.
- Use AWS Secrets Manager or SSM Parameter Store in mature environments instead of plain-text `.env` files.
- Put the RDS instance in private subnets with no public access.
- Keep EC2 and RDS security groups tightly scoped.

## Quick Start Summary

```bash
cd automobile-manufacturing-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export FLASK_APP=app.py
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
python seed.py
flask run --host 0.0.0.0 --port 5000
```
