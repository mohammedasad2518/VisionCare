import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from ..core.config import settings

logger = logging.getLogger(__name__)

# Configure engine for SQLite (ensuring multi-thread compatibility for FastAPI requests)
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """
    FastAPI dependency yielding a thread-safe database session
    and ensuring guaranteed cleanup/closure.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initializes database tables in SQLite.
    Called on FastAPI application startup.
    """
    try:
        settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized successfully at '{settings.DATABASE_PATH}'.")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}", exc_info=True)
        raise

