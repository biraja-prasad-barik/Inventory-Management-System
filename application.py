#!/usr/bin/env python3
"""
Flask application entry point for Render deployment
This avoids naming conflicts with the app/ folder
"""
import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, db

# Create the Flask application using the factory pattern
app = create_app()

# Initialize database on first run
with app.app_context():
    db.create_all()
    print("Database initialized successfully!")

if __name__ == '__main__':
    # For local development - proper port binding for Render
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host="0.0.0.0", port=port)