This project is configured for Flask-Migrate.

Generate migration files after configuring `.env` and installing dependencies:

1. flask db init        # run once if migrations have not been initialized
2. flask db migrate -m "Initial schema"
3. flask db upgrade

If you prefer to check migration artifacts into version control, commit the generated `migrations/` directory after running the commands above in your environment.
