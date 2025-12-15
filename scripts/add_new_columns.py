import sys
import os
import random
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from models.user import User

def add_columns():
    # 1. Schema Migration
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            print("Attempting to add nickname column to users...")
            try:
                conn.execute(text("ALTER TABLE users ADD COLUMN nickname VARCHAR(64)"))
                conn.execute(text("CREATE UNIQUE INDEX ix_users_nickname ON users (nickname)"))
                print("Added nickname column.")
            except Exception as e:
                print(f"Skipping nickname add (might exist): {e}")

            print("Attempting to add title column to drawings...")
            try:
                conn.execute(text("ALTER TABLE drawings ADD COLUMN title VARCHAR(255)"))
                print("Added title column.")
            except Exception as e:
                print(f"Skipping title add (might exist): {e}")

            trans.commit()
        except Exception as e:
            trans.rollback()
            print(f"Schema migration failed: {e}")
            return

    # 2. Data Backfill
    print("Backfilling nicknames for existing users...")
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    try:
        users = session.query(User).filter(User.nickname == None).all()
        count = 0
        for user in users:
            # Simple retry logic for uniqueness
            for _ in range(10):
                suffix = str(random.randint(1000, 9999))
                nick = f"用户_{suffix}"
                if not session.query(User).filter(User.nickname == nick).first():
                    user.nickname = nick
                    count += 1
                    break
        
        session.commit()
        print(f"Backfilled {count} users.")
    except Exception as e:
        session.rollback()
        print(f"Backfill failed: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    add_columns()
