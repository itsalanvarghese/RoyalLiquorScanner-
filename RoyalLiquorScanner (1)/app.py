import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

# Configuration
app.config["DEBUG"] = True  # Enable debug mode for development
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
db.init_app(app)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return {"error": "Not found"}, 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return {"error": "Internal server error"}, 500

# Initialize database and routes
with app.app_context():
    import models  # Import models after db initialization
    import routes  # Import routes after models
    
    try:
        db.create_all()
    except Exception as e:
        print(f"Database initialization error: {e}")
