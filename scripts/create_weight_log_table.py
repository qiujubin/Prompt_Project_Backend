import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from database import engine, Base
from models.weight_log import WeightLog

def create_table():
    print("Creating weight_logs table...")
    Base.metadata.create_all(bind=engine)
    print("Table created successfully!")

if __name__ == "__main__":
    create_table()
