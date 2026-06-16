import logging
import os
import sys
from datetime import datetime

from flask import Flask, render_template, request
from werkzeug.middleware.proxy_fix import ProxyFix

from config import Config
from extensions import csrf, db, login_manager, migrate
from models import User
from routes import main_bp


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def configure_logging(app: Flask) -> None:
    log_level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)

    if not app.logger.handlers:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
        )
        app.logger.addHandler(stream_handler)

    app.logger.setLevel(log_level)
    logging.getLogger().setLevel(log_level)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

    configure_logging(app)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_global_context():
        return {"current_year": datetime.utcnow().year}

    @app.before_request
    def make_session_permanent():
        from flask import session

        session.permanent = True

    @app.after_request
    def set_security_headers(response):
        csp = (
            "default-src 'self'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "connect-src 'self';"
        )
        response.headers.setdefault("Content-Security-Policy", csp)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault(
            "Permissions-Policy", "camera=(), microphone=(), geolocation=()"
        )
        if request.is_secure:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        return response

    @app.errorhandler(404)
    def not_found(error):
        return render_template(
            "error.html",
            title="Page Not Found",
            code=404,
            message="The page you are looking for does not exist.",
        ), 404

    @app.errorhandler(500)
    def server_error(error):
        db.session.rollback()
        app.logger.exception("Unhandled internal server error: %s", error)
        return render_template(
            "error.html",
            title="Server Error",
            code=500,
            message="An unexpected error occurred. Please try again later.",
        ), 500

    app.logger.info("Application startup complete.")
    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host=os.getenv("FLASK_RUN_HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "5000")),
        debug=app.config["DEBUG"],
    )
