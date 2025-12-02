import sys
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add backend directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.config import settings

def fix_schema():
    print(f"Connecting to database: {settings.DB_URL}")
    engine = create_engine(settings.DB_URL)
    
    with engine.connect() as conn:
        try:
            print("Adding prompt_id column to drawings table...")
            conn.execute(text("ALTER TABLE drawings ADD COLUMN prompt_id VARCHAR(64)"))
            conn.execute(text("CREATE INDEX ix_drawings_prompt_id ON drawings (prompt_id)"))
            print("Column added successfully.")
        except Exception as e:
            print(f"Error adding column (might already exist): {e}")
            
    print("Schema fix completed.")

if __name__ == "__main__":
    fix_schema()
