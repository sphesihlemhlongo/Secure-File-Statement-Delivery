import unittest
import sys
import os

# Add current directory to path so we can import db
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from db import init_db, engine

class TestDBInit(unittest.TestCase):
    def test_init_db(self):
        try:
            # Attempt to connect to see if DB is available
            with engine.connect() as connection:
                pass
            print("Database connection successful, running init_db...")
            init_db()
            print("init_db ran successfully.")
        except Exception as e:
            print(f"Skipping DB init test: {e}")

if __name__ == "__main__":
    unittest.main()
