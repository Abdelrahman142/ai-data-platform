from sqlalchemy import create_engine, text
from app.config import settings

engine = create_engine(settings.DATABASE_URL)

print("Fixing username column nullable constraint...")
try:
    with engine.begin() as conn:
        # Make username nullable
        conn.execute(text("ALTER TABLE users ALTER COLUMN username DROP NOT NULL;"))
    print("Success: username is now nullable.")
except Exception as e:
    print(f"Error: {e}")
