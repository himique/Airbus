# crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update as sqlalchemy_update
from sqlalchemy import delete as sqlalchemy_delete

from sqlalchemy.exc import IntegrityError # Для обработки ошибок уникальности

import models
import schemas
from auth import auth
# --- CRUD Operations for Items ---
async def create_user(db: AsyncSession, user: schemas.UserCreate) -> models.User:
    """Создает нового пользователя в базе данных."""
    # Хешируем пароль перед сохранением
    hashed_pass = auth.hash_password(user.password)

    # Создаем объект модели SQLAlchemy
    db_user = models.User(
        user=user.user,
        email=user.email,
        password=hashed_pass # Сохраняем хеш!
    )
    db.add(db_user)
    
    try:
        # Сохраняем изменения в БД
        await db.commit()
        # Обновляем объект, чтобы получить ID из БД
        await db.refresh(db_user)
        print(f"Пользователь {db_user.user} успешно создан с ID {db_user.id}.")
        return db_user
    except IntegrityError as e:
        # Если нарушение уникальности (user или email уже существуют)
        await db.rollback() # Откатываем транзакцию
        print(f"Ошибка IntegrityError при создании пользователя: {e}")
        # Можно выбросить HTTPException или вернуть None/специальный объект ошибки
        raise ValueError(f"Пользователь с таким именем '{user.user}' или email '{user.email}' уже существует.")
    except Exception as e:
        # Другие возможные ошибки
        await db.rollback()
        print(f"Непредвиденная ошибка при создании пользователя: {e}")
        raise e # Перевыбрасываем ошибку для обработки выше

async def get_user_by_email(db: AsyncSession, email: str) -> models.User | None:
     stmt = select(models.User).where(models.User.email == email)
     result = await db.execute(stmt)
     return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str) -> models.User | None:
     stmt = select(models.User).where(models.User.user == username)
     result = await db.execute(stmt)
     return result.scalar_one_or_none()
     
async def get_user_by_id(db: AsyncSession, user_id: int) -> models.User | None:
    """Fetches a single item by its ID."""
    stmt = select(models.User).filter(models.User.id == user_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() # .first() returns one or None

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100)-> models.User | None:
    """Fetches multiple items with pagination."""
    result = await db.execute(select(models.User).offset(skip).limit(limit))
    return result.scalars().all()


async def update_user(db: AsyncSession, user_id: int, user_update: schemas.ItemUpdate):
    """Updates an existing item."""
    db_item = await get_user_by_id(db, user_id)
    if not db_item:
        return None # Item not found

    # Get the update data, excluding unset fields to avoid overwriting with None
    update_data = user_update.dict(exclude_unset=True)

    # Update the SQLAlchemy model instance
    for key, value in update_data.items():
        setattr(db_item, key, value)

    db.add(db_item) # Add the updated object to the session
    await db.commit()
    await db.refresh(db_item)
    return db_item

    # Alternative using SQLAlchemy update statement (potentially more efficient for many fields)
    # if not update_data:
    #     return db_item # No fields to update

    # statement = (
    #     sqlalchemy_update(models.Item)
    #     .where(models.Item.id == item_id)
    #     .values(**update_data)
    #     .execution_options(synchronize_session="fetch") # Important for async updates
    # )
    # await db.execute(statement)
    # await db.commit()
    # # Re-fetch or refresh might be needed depending on how you want the return value
    # return await get_item(db, item_id)
async def get_item_by_id(db: AsyncSession, user_id: int) -> models.Item | None:
    """Fetches a single item by its ID."""
    stmt = select(models.Item).filter(models.Item.owner_id == user_id)
    result = await db.execute(stmt)
    return result.scalars().all() # .first() returns one or None


async def delete_user(db: AsyncSession, user_id: int):
    """Deletes an item from the database."""
    db_user = await get_user_by_id(db, user_id)
    if not db_user:
        return None # Item not found
    await db.delete(db_user)
    await db.commit()
    return db_user # Return the deleted item data (optional)

    # Alternative using SQLAlchemy delete statement
    # statement = sqlalchemy_delete(models.Item).where(models.Item.id == item_id)
    # result = await db.execute(statement)
    # await db.commit()
    # if result.rowcount == 0:
    #     return None # Item not found
    # return {"message": "Item deleted successfully", "id": item_id} # Return confirmation



    # Shoping cart

async def create_shoping_card_item(id: int, db: AsyncSession, item: schemas.ItemBase) -> models.Item:
    """Создает нового пользователя в базе данных."""
    # Создаем объект модели SQLAlchemy
    db_item = models.Item(
        name=item.name,
        description=item.description,
        price=item.price, # Сохраняем хеш!
        owner_id=id
    )
    db.add(db_item)
    
    try:
        # Сохраняем изменения в БД
        await db.commit()
        # Обновляем объект, чтобы получить ID из БД
        await db.refresh(db_item)
        print(f"Товар '{db_item.name}' успешно создан для пользователя ID {db_item.owner_id} с ID товара {db_item.id}.")
        return db_item
    except IntegrityError as e:
        await db.rollback()
        print(f"Ошибка IntegrityError при создании товара: {e}")
        # Возможно, такое имя товара уже есть? Зависит от вашей логики.
        raise ValueError(f"Ошибка при создании товара: {e}")
    except Exception as e:
        await db.rollback()
        print(f"Непредвиденная ошибка при создании товара: {e}")
        raise e