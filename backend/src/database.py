# database.py
import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv() # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")

# Create an asynchronous engine
# pool_recycle: Reconnect after this many seconds of inactivity. -1 = disable.
# pool_pre_ping: Test connections for liveness before using them.
engine = create_async_engine(
    DATABASE_URL,
    echo=True, # Log SQL queries (good for debugging)
    pool_recycle=3600,
    pool_pre_ping=True
)

# Create a session factory bound to the engine
# expire_on_commit=False prevents detached instance errors in async contexts
AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False, # Recommended for async operations
)

# Base class for our SQLAlchemy models
Base = declarative_base()

# Dependency function to get a DB session per request

# Function to create database tables (run once at startup or via a script)
async def create_tables():
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Use with caution! Drops all tables.
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created (if they didn't exist).")