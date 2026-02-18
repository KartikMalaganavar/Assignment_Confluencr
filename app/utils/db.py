from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.utils.config import settings


class Base(DeclarativeBase):
    pass


engine = create_engine(
    settings.database_url,
    pool_pre_ping=False,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    connect_args={"options": f"-c timezone={settings.db_timezone}"},
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def ensure_tables_exist() -> None:
    # checkfirst=True is the default: creates only missing objects.
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
