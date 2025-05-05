# backend/alembic/env.py
import os
import sys
from logging.config import fileConfig
from sqlalchemy.ext.asyncio import create_async_engine # Use async engine
from sqlalchemy import pool
from alembic import context

# --- Load .env variables ---
# Add the 'src' directory to the Python path to find modules
# Adjust the path '../src' if your alembic folder is elsewhere relative to src
SRC_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'src')
sys.path.append(SRC_PATH)

# Load dotenv from the expected location (e.g., inside src)
from dotenv import load_dotenv
DOTENV_PATH = os.path.join(SRC_PATH, '.env')
if os.path.exists(DOTENV_PATH):
    load_dotenv(DOTENV_PATH)
    print(f"Loaded environment variables from {DOTENV_PATH}") # Debug print
else:
    print(f".env file not found at {DOTENV_PATH}") # Debug print


# --- Alembic Configuration ---
# Interpret the config file for Python logging.
# This line sets up loggers basically.
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)

# --- Model Metadata ---
# Import your Base metadata object from your models file
# Adjust the import path if your models.py is located differently
try:
    from backend.src.models import Base # Assuming models.py is directly in src/
except ImportError:
    raise ImportError("Could not import 'Base' from 'models'. Ensure models.py is in backend/src/ and sys.path is correct.")

target_metadata = Base.metadata

# --- Database URL ---
# Get the database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set or .env not loaded")
print(f"Using DATABASE_URL: {DATABASE_URL[:15]}...") # Debug print (don't print full URL with password)

# --- Migration Functions ---
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    # Use the dynamically loaded DATABASE_URL
    context.configure(
        url=DATABASE_URL, # Use the loaded URL
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Helper function to run migrations using a connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Create an ASYNC engine using the loaded DATABASE_URL
    connectable = create_async_engine(
        DATABASE_URL,
        poolclass=pool.NullPool # Use NullPool for migration engine
    )

    # Use the async engine's connect method
    async with connectable.connect() as connection:
        # Run the migrations within the async connection's run_sync method
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine when done
    await connectable.dispose()


# Determine whether to run online or offline
if context.is_offline_mode():
    print("Running migrations offline...")
    run_migrations_offline()
else:
    print("Running migrations online...")
    import asyncio
    # Run the async online migration function
    asyncio.run(run_migrations_online())

print("Migration process finished.")