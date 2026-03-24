from app.database import engine, Base
from app.models.user import User
from app.models.dataset import Dataset, DatasetMetadata, ProcessingLog, DatasetShare, ActivityLog

def init_db():
    print("Creating tables in database...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

if __name__ == "__main__":
    init_db()
