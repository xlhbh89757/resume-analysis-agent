import sys
import os
sys.path.append(os.getcwd())

from src.core.database import engine, Base
from src.models import *  # Import all models to ensure they are registered

def reset_db():
    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset successfully!")

if __name__ == "__main__":
    reset_db()
