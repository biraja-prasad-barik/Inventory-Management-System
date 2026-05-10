"""
One-time migration script to add 'username' column to the existing 'user' table.
Safe to run multiple times - it checks if the column already exists first.
"""
from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    # Check if column already exists
    result = db.session.execute(text(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='user' AND column_name='username'"
    ))
    if result.fetchone():
        print("Column 'username' already exists. No changes needed.")
    else:
        db.session.execute(text(
            "ALTER TABLE \"user\" ADD COLUMN username VARCHAR(80)"
        ))
        db.session.commit()
        print("Column 'username' added to 'user' table successfully.")
