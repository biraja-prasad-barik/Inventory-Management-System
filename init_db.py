#!/usr/bin/env python3
"""
Database initialization script for Inventory Pro
"""
from app import create_app, db
from app.models import User, Item

def init_database():
    app = create_app()
    
    with app.app_context():
        # Create all tables
        db.create_all()
        print("Database tables created successfully!")
        
        # Check if admin user exists
        admin_user = User.query.filter_by(email='admin@inventrypro.com').first()
        if not admin_user:
            # Create admin user
            admin_user = User(email='admin@inventrypro.com')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Admin user created: admin@inventrypro.com / admin123")
            print("Database is ready - you can now add your own inventory items!")
        else:
            print("Admin user already exists!")

if __name__ == '__main__':
    init_database()