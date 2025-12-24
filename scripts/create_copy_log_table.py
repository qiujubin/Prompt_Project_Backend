import sys
import os
from sqlalchemy import text

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from models.copy_log import CopyLog

def migrate():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Creating copy_logs table...")
            CopyLog.__table__.create(conn)
            print("Table copy_logs created.")
            
            # Optional: Drop the temporary columns from users if they exist
            # Commenting out for safety, user can decide to drop later or we keep them as cache
            # But the user specifically said "directly adding two fields is not good", so let's clean up
            print("Cleaning up temporary columns from users table...")
            try:
                conn.execute(text("ALTER TABLE users DROP COLUMN copy_positive_count"))
                print("Dropped copy_positive_count.")
            except Exception as e:
                print(f"Skipping drop copy_positive_count: {e}")
                
            try:
                conn.execute(text("ALTER TABLE users DROP COLUMN copy_negative_count"))
                print("Dropped copy_negative_count.")
            except Exception as e:
                print(f"Skipping drop copy_negative_count: {e}")

            trans.commit()
            print("Migration completed successfully.")
        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
