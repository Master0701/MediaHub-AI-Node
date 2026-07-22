from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class Setting(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True)
    key = Column(
        String(100),
        unique=True,
        nullable=False,
    )
    value = Column(Text)
    created = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    job_type = Column(
        String(100),
        nullable=False,
    )
    status = Column(
        String(50),
        nullable=False,
        default="queued",
    )
    progress = Column(
        Integer,
        nullable=False,
        default=0,
    )
    payload = Column(Text)
    result = Column(Text)
    error = Column(Text)

    created = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated = Column(
        DateTime(timezone=True),
        onupdate=func.now(),
    )
    started = Column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished = Column(
        DateTime(timezone=True),
        nullable=True,
    )


class Provider(Base):
    __tablename__ = "providers"

    id = Column(Integer, primary_key=True)
    name = Column(
        String(100),
        unique=True,
    )
    enabled = Column(
        Integer,
        default=1,
    )
    config = Column(Text)
