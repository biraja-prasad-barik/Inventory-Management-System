#!/usr/bin/env python3
"""
Database initialization script for Inventory Pro
"""
from app import create_app, db

def init_database():
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        print("Database is ready!")
        print("Go to /signup to create your first account manually")

if __name__ == '__main__':
    init_database()