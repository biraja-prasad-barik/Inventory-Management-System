#!/usr/bin/env python3
"""
Clear all inventory data and reset to zero
"""
from app import create_app, db
from app.models import Item, Customer, Invoice

def clear_all_data():
    app = create_app()
    
    with app.app_context():
        # Delete all items
        Item.query.delete()
        
        # Delete all customers
        Customer.query.delete()
        
        # Delete all invoices
        Invoice.query.delete()
        
        # Commit the changes
        db.session.commit()
        
        print("All inventory data cleared successfully!")
        print("Dashboard will now show zero values.")
        print("You can now add your own items manually.")

if __name__ == '__main__':
    clear_all_data()