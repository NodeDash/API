from sqlalchemy import Column, Integer, String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base
from app.models.enums import OwnerType


class Flow(Base):
    __tablename__ = "flows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True, index=True)
    description = Column(String, nullable=True)
    nodes = Column(JSON, nullable=True)
    edges = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # Add owner fields
    owner_id = Column(Integer, nullable=True)
    owner_type = Column(String, default=OwnerType.USER)
    # Note: owner_id references either users.id or teams.id depending on owner_type
    # No foreign key constraint to support polymorphic ownership

    # Flow layout is stored separately
    layout = Column(JSON, nullable=True)

    # Note: owner relationship removed due to polymorphic ownership
