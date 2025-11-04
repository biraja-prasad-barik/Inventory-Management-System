#!/usr/bin/env python3
"""
Clear all data and reset to zero - including users
"""
from app import create_app, db
from app.models import User, Item, Customer, Invoice

def clear_all_data():
    app = create_app()
    
    with app.app_context():
        # Delete all users (so you can create manually)
        User.query.delete()
        
        # Delete all items
        Item.query.delete()
        
        # Delete all customers
        Customer.query.delete()
        
        # Delete all invoices
        Invoice.query.delete()
        
        # Commit the changes
        db.session.commit()
        
        print("All data cleared successfully!")
        print("Database is completely empty - you can now:")
        print("1. Create your own account manually via signup")
        print("2. Add your own inventory items")
        print("3. Add your own customers and invoices")

if __name__ == '__main__':
    clear_all_data()