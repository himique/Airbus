from sqlalchemy.ext.asyncio import AsyncSession
import models, schemas
from sqlalchemy import func as sql_func
from fastapi import HTTPException, status
from sqlalchemy.future import select
from sqlalchemy import update
from sqlalchemy import delete 
from fastapi import HTTPException, status
import crud
from auth import auth
from sqlalchemy.exc import SQLAlchemyError, NoResultFound
async def create_post(db: AsyncSession, post: schemas.PostCreate, owner_user: str):
    db_post_data = post.model_dump()
    db_post = models.Post(
        **db_post_data, # Распаковываем данные из схемы
        post_owner_user=owner_user, # Устанавливаем владельца
        already_engaged=0 #Default value
    )
    db.add(db_post) # Добавляем объект в сессию
    try:    
        await db.commit()     # Сохраняем изменения в БД
        await db.refresh(db_post) # Обновляем объект из БД (чтобы получить сгенерированный post_id и др.)
        return db_post
    except Exception as e:
        # Другие возможные ошибки
        await db.rollback()
        print(f"Непредвиденная ошибка при создании поста: {e}")
        raise e # Перевыбрасываем ошибку для обработки выше

async def add_member_to_post(db: AsyncSession, post_id: int, username_to_add: str) -> models.Post:
    """
    Добавляет пользователя как участника к посту.
    Обновляет количество занятых мест (already_engaged) в посте.
    Проверяет, не превышено ли максимальное количество мест.
    """
    # 1. Получаем пост из БД
    db_post = await db.get(models.Post, post_id)
    if not db_post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # --- 2. Проверяем, существует ли пользователь, которого добавляем ---
    # SELECT * FROM users WHERE "user" = :username_to_add
    user_select_stmt = select(models.User).where(models.User.user == username_to_add)
    result_user = await db.execute(user_select_stmt)
    db_user_to_add = result_user.scalar_one_or_none()

    if not db_user_to_add:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username_to_add}' to add not found."
        )
    
     # ---  Проверяем, является ли пользователь, которого добавляем владельцев---
    # --- КОНЕЦ ПРОВЕРКИ 2 ---
     # --- ПРОВЕРКА: НЕ ЯВЛЯЕТСЯ ЛИ ДОБАВЛЯЕМЫЙ ПОЛЬЗОВАТЕЛЬ ВЛАДЕЛЬЦЕМ ПОСТА ---
    # Получаем объект владельца поста (если нужно сравнивать объекты или их ID)
    # Предполагаем, что db_post.post_owner_user_fk хранит имя пользователя владельца
    owner_username = db_post.post_owner_user
    if owner_username == db_user_to_add.user: # Сравниваем имена пользователей (если FK это username)
         # или owner_user_id == user_to_add.id (если FK это ID)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # Используем 400 Bad Request
            detail=f"User '{username_to_add}' is the owner of the post and cannot be added as a member."
        )
   
    # --- 3. Проверяем, не является ли пользователь уже участником этого поста ---
    # SELECT * FROM post_members WHERE post_id_fk = :post_id AND member_user_fk = :username_to_add
    membership_select_stmt = select(models.PostMember).where(
        models.PostMember.post_id == post_id,
        models.PostMember.member_user == db_user_to_add.user # или db_user_to_add.user, если хотите быть уверены
    )
    result_membership = await db.execute(membership_select_stmt)
    existing_membership = result_membership.scalar_one_or_none()

    if existing_membership:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, # 400 Bad Request или 409 Conflict
            detail=f"User '{username_to_add}' is already a member of this post."
        )
    # --- КОНЕЦ ПРОВЕРКИ 3 ---

    # 4. Проверяем, есть ли свободные места (ключевая проверка из предыдущего ответа)
    stmt_count_members = sql_func.count(models.PostMember.post_id) # SQLAlchemy func для COUNT
    query_count_members = await db.execute(
        select(stmt_count_members).where(models.PostMember.post_id == post_id)
    )
    current_actual_members_count = query_count_members.scalar_one_or_none() or 0

    if current_actual_members_count >= db_post.count_of_places:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No available places in this post."
        )

    # 5. Если все проверки пройдены, создаем новую запись о членстве
    new_member_entry = models.PostMember(
        post_id=post_id,
        member_user=username_to_add # Используем оригинальное имя пользователя
    )
    db.add(new_member_entry)

    # 6. Обновляем поле already_engaged в посте
    db_post.already_engaged = current_actual_members_count + 1
    # db.add(db_post) # Для обновлений существующих отслеживаемых объектов db.add() не всегда нужен,
                     # SQLAlchemy отслеживает изменения. Но его наличие не повредит.

    try:
        await db.commit()
        await db.refresh(db_post) # Обновить объект поста
    except Exception as e: # Важно ловить конкретные ошибки SQLAlchemy, если возможно (например, IntegrityError)
        await db.rollback()
        # Логирование ошибки
        print(f"DATABASE ERROR when adding member to post {post_id} for user {username_to_add}: {e}")
        # Можно проверить тип ошибки, например, если это IntegrityError из-за гонки состояний
        # if isinstance(e, sqlalchemy.exc.IntegrityError):
        #     raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflict while adding member, possibly due to concurrent update.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not add member to post: {str(e)}")

    return db_post

async def get_posts(db: AsyncSession,  skip: int = 0, limit: int = 100) -> models.Post | None:
    result = await db.execute(select(models.Post).offset(skip).limit(limit))
    return result.scalars().all()

async def get_posts_from_owner(db: AsyncSession, post_user: str, skip: int = 0, limit: int = 100) -> models.Post | None:
    stmt = select(models.Post).where(models.Post.post_owner_user == post_user)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()

async def get_post_by_id(db: AsyncSession, post_id: int)-> models.Post | None:
    stmt = select(models.Post).where(models.Post.post_id == post_id)
    try:
        result = await db.execute(stmt)
        post = result.scalar_one() # This will raise NoResultFound if no post
        return post
    except NoResultFound:
        raise HTTPException(
            status_code=404,
            detail=f"Пост с ID {post_id} не найден."
        )
    except SQLAlchemyError as e:
        # Log e
        print(f"Database error: {e}")
        raise HTTPException(
            status_code=500,
            detail="An error occurred while fetching the post from the database."
        )

async def delete_post_by_id(db: AsyncSession, post_id: int, user: models.User)-> models.Post | None:
    db_post = await get_post_by_id(db, post_id)
    if not db_post:
        return None # Item not found
    is_owner = (user.user == db_post.post_owner_user)
    is_admin = False
    if not is_owner:
        await auth.require_admin_user(user)
        is_admin=True
    if is_owner or is_admin:
        await db.delete(db_post)
        await db.commit()
        return db_post
    else:
        # Если ни владелец, ни админ (и проверка на админа не выбросила исключение)
        raise HTTPException(
            status_code=403,
            detail="У вас нет прав для удаления этого поста."
        )