from flask import Flask, jsonify
from .extensions import db, migrate, jwt, cors
from .auth.routes import auth_bp
from .shipments.routes import shipments_bp
from .admin.routes import admin_bp
from config import config

def create_app(env="development"):
    app = Flask(__name__)
    app.config.from_object(config[env])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, origins=app.config.get("CORS_ORIGINS", "*"), supports_credentials=True)

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(shipments_bp)
    app.register_blueprint(admin_bp)

    # Global error handler (for Marshmallow/validation)
    @app.errorhandler(422)
    @app.errorhandler(400)
    def handle_validation_error(err):
        return jsonify({"error": "Invalid input"}), 400

    @app.errorhandler(404)
    def not_found(err):
        return jsonify({"error": "Not found"}), 404

    return app
