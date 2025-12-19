import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

def fix_trigger():
    print("Attempting to fix database triggers...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Check if table has updated_at column
            # Use raw connection for simple check to avoid transaction issues in previous attempt
            try:
                conn.execute(text("SELECT updated_at FROM user_favorites LIMIT 1"))
                print("user_favorites already has updated_at column.")
            except Exception:
                print("user_favorites does NOT have updated_at column. Adding it...")
                # We need to rollback the failed select to proceed in same transaction? 
                # Or just proceed. In SQLAlchemy, if an error occurs, the transaction is invalidated.
                # So we should restart transaction or handle carefully.
                pass
        except Exception:
             pass
             
    # New connection for clean slate
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Try to add the column. If it exists, this will fail, so we wrap in try/except or check safely
            # Postgres: ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...
            conn.execute(text("ALTER TABLE user_favorites ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()"))
            print("Ensured updated_at column exists.")
            trans.commit()
        except Exception as e:
            print(f"Error adding column: {e}")
            trans.rollback()
        
        print("Fix complete.")

if __name__ == "__main__":
    fix_trigger()
