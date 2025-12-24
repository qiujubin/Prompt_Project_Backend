import sys
import os
from sqlalchemy import text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine

def add_columns():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Attempting to add copy_positive_count column to users...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN copy_positive_count BIGINT DEFAULT 0"))
                print("Added copy_positive_count column.")
            except Exception as e:
                print(f"Skipping copy_positive_count add (might exist): {e}")

            print("Attempting to add copy_negative_count column to users...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN copy_negative_count BIGINT DEFAULT 0"))
                print("Added copy_negative_count column.")
            except Exception as e:
                print(f"Skipping copy_negative_count add (might exist): {e}")

            trans.commit()
            print("Migration completed successfully.")
        except Exception as e:
            trans.rollback()
            print(f"Schema migration failed: {e}")

if __name__ == "__main__":
    add_columns()
