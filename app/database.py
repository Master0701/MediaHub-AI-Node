from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_FILE = Path("/opt/mediahub/database/mediahub_ai.db")

engine = create_engine(
    f"sqlite:///{DATABASE_FILE}",
    future=True,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()
