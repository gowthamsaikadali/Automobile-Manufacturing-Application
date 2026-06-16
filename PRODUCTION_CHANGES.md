# Production hardening changes applied

This project was updated for safer cloud deployment with the following code-level improvements:

## 1. Configuration hardening
Updated `config.py` to include:
- boolean and integer environment parsing helpers
- normalization for `postgres://` URLs to `postgresql://`
- SQLAlchemy connection pool settings for RDS
- configurable log level
- preferred URL scheme
- session lifetime configuration
- optional `HEALTHCHECK_TOKEN`

## 2. App security and logging
Updated `app.py` to include:
- structured stdout logging for Gunicorn/systemd
- permanent session handling
- stronger HTTP response headers:
  - Content-Security-Policy
  - Permissions-Policy
  - HSTS when HTTPS is used
  - X-Content-Type-Options
  - X-Frame-Options
  - Referrer-Policy
- better 500 error logging
- `db.session.get()` for the Flask-Login user loader

## 3. Health check endpoint
Updated `routes.py` with:
- `GET /health`
- optional token protection via `X-Health-Token`
- database connectivity probe using `SELECT 1`
- proper `200` or `503` status output for load balancers/monitoring

## 4. Better operational logging
Updated `routes.py` to log:
- successful logins
- failed login attempts
- logouts
- DB write failures in materials, production, inventory, and profile flows

## 5. Safer production seeding
Updated `seed.py` with:
- `--admin-only` mode for production bootstrap
- `--reset-admin-password` mode
- default local/demo seeding behavior retained

## 6. Added production environment template
Added `.env.production.example` for EC2/RDS deployment.

## Recommended production bootstrap

```bash
cp .env.production.example .env
# edit values
python seed.py --admin-only
```

## Recommended runtime

```bash
gunicorn --workers 3 --bind 0.0.0.0:5000 wsgi:app
```
