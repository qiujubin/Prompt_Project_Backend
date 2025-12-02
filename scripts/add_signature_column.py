import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

def add_signature_column():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN signature TEXT;"))
            conn.commit()
            print("Successfully added signature column to users table.")
        except Exception as e:
            print(f"Error adding column (it might already exist): {e}")

if __name__ == "__main__":
    add_signature_column()
