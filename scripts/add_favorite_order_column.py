import sys
import os
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine

def add_columns():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Attempting to add display_order column to user_favorites...")
            try:
                # Add display_order column, defaulting to 0
                conn.execute(text("ALTER TABLE user_favorites ADD COLUMN display_order INTEGER DEFAULT 0"))
                print("Added display_order column.")
            except Exception as e:
                print(f"Skipping display_order add (might exist): {e}")

            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Schema migration failed: {e}")
            return

if __name__ == "__main__":
    add_columns()
