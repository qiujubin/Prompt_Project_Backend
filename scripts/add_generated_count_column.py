import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import text
from database import engine

def add_column():
    print("Adding generated_count column to user_prompt_keywords...")
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE user_prompt_keywords ADD COLUMN generated_count INTEGER DEFAULT 0"))
            print("Column added successfully!")
            conn.commit()
        except Exception as e:
            print(f"Error adding column: {e}")
            # If column exists, it might throw error, which is fine
            pass

if __name__ == "__main__":
    add_column()
