from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    status = Column(String, default="uploaded")  # uploaded, processing, ready, failed
    raw_file_path = Column(String)
    processed_file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="datasets")
    metadata_info = relationship("DatasetMetadata", back_populates="dataset", uselist=False)
    logs = relationship("ProcessingLog", back_populates="dataset")
    shares = relationship("DatasetShare", back_populates="dataset")


class DatasetMetadata(Base):
    __tablename__ = "dataset_metadata"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), unique=True, nullable=False)
    rows_count = Column(Integer)
    columns_count = Column(Integer)
    missing_ratio = Column(Float)
    size_mb = Column(Float)

    dataset = relationship("Dataset", back_populates="metadata_info")


class ProcessingLog(Base):
    __tablename__ = "processing_logs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    step_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    message = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="logs")


class DatasetShare(Base):
    __tablename__ = "dataset_shares"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission = Column(String, default="view")  # view, edit
    shared_at = Column(DateTime, default=datetime.utcnow)

    dataset = relationship("Dataset", back_populates="shares")
    user = relationship("User")


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String, nullable=False)  # upload, clean, share, ai_query, export
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
