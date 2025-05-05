from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

# Импортируйте вашу фабрику сессий из файла database.py
# Убедитесь, что путь импорта правильный (может быть .database или database)
from database import AsyncSessionFactory

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function that yields an AsyncSession for use in a request.
    Ensures the session is closed afterwards.
    """
    async with AsyncSessionFactory() as session:
        # Вы можете добавить сюда логику начала транзакции, если нужно
        try:
            yield session
        except Exception:
            await session.rollback() # Откат при ошибке
            raise
        finally:
            await session.close() # async with закроет автоматически