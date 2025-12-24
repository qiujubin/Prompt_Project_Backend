import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from database import engine

def add_columns():
    print("Adding generation timestamps to user_prompt_keywords (PostgreSQL)...")
    
    # Add last_generated_at
    try:
        with engine.connect() as conn:
            print("Adding last_generated_at...")
            # Use TIMESTAMP WITH TIME ZONE for Postgres
            conn.execute(text("ALTER TABLE user_prompt_keywords ADD COLUMN last_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL"))
            conn.commit()
            print("last_generated_at added.")
    except Exception as e:
        print(f"Error adding last_generated_at: {e}")

    # Add first_generated_at
    try:
        with engine.connect() as conn:
            print("Adding first_generated_at...")
            conn.execute(text("ALTER TABLE user_prompt_keywords ADD COLUMN first_generated_at TIMESTAMP WITH TIME ZONE DEFAULT NULL"))
            conn.commit()
            print("first_generated_at added.")
    except Exception as e:
        print(f"Error adding first_generated_at: {e}")
            
    print("Done.")

if __name__ == "__main__":
    add_columns()
