# main.py
from fastapi import FastAPI, Depends, HTTPException, status, Response, Request, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Annotated, Optional # Use standard List typing
from pydantic import ValidationError 
import models
import crud
import schemas
from enums import CountriesCapitals, UserRole
from auth import auth
from database import engine, create_tables # Import necessary components
from depencies import get_db
from posts import posts

from fastapi.security import OAuth2PasswordRequestForm



# --- FastAPI App Initialization ---
app = FastAPI(
    title="FastAPI PostgreSQL API",
    description="Education API",
    version="0.2.0",
)

# --- API Endpoints ---

@app.post("/logout", summary="Logout and set auth cookie", response_model=schemas.Message, tags=["Login system"])
async def logout(
    response: Response, # Нужен для установки cookie
    
):


    # Устанавливаем cookie
    response.set_cookie(
        key=auth.ACCESS_TOKEN_COOKIE_NAME,
        value="",
        httponly=True,  # !!! Важно: Защита от XSS
        samesite='lax', # !!! Важно: Защита от CSRF (lax или strict)
        secure=False,   # !!! ВАЖНО: В продакшене с HTTPS установите True !!!
        max_age=0,      # Время жизни в секундах
        path="/",       # Cookie доступна для всего сайта
    )
    # print(f"Cookie set for user: {user.username}") # Отладка
    return {"message": "Logout successful"}


@app.post("/login", summary="Login and set auth cookie", response_model=schemas.Message, tags=["Login system"])
async def login(
    response: Response, # Нужен для установки cookie
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()], # Стандартная форма логин/пароль
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Проверяет имя пользователя и пароль. В случае успеха создает JWT
    и устанавливает его в httpOnly cookie.
    """
    user = await crud.get_user_by_username(db, username=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Пароль верный, создаем токен
    access_token = auth.create_access_token(data={"sub": user.user})

    # Устанавливаем cookie
    response.set_cookie(
        key=auth.ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        httponly=True,  # !!! Важно: Защита от XSS
        samesite='lax', # !!! Важно: Защита от CSRF (lax или strict)
        secure=False,   # !!! ВАЖНО: В продакшене с HTTPS установите True !!!
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60, # Время жизни в секундах
        path="/",       # Cookie доступна для всего сайта
    )
    # print(f"Cookie set for user: {user.username}") # Отладка
    return {"message": "Login successful"}

@app.post("/register", summary="Register a new user", response_model=schemas.UserPublic, status_code=status.HTTP_201_CREATED, tags=["Login system"])
async def register(
    user_in: schemas.UserCreate,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """Создает нового пользователя."""
    db_user = await crud.get_user_by_username(db, username=user_in.user)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    new_user = await crud.create_user(db=db, user=user_in)
    return new_user # Pydantic автоматически преобразует благодаря orm_mode/from_attributes

@app.get("/users/me", summary="Get current user info", response_model=schemas.UserPublic, tags=["Login system"])
async def read_users_me(
    current_user: Annotated[models.User, Depends(auth.get_current_user)] # Зависимость проверяет аутентификацию
):
    """Возвращает информацию о текущем аутентифицированном пользователе."""
    # Если запрос дошел сюда, значит пользователь аутентифицирован
    return current_user

# Маршрут ТОЛЬКО для Администраторов
@app.get("/admin/dashboard", response_model=schemas.Message, tags=["Admin"])
async def admin_dashboard(
    # Используем новую зависимость для проверки роли АДМИНА
    admin_user: Annotated[models.User, Depends(auth.require_admin_user)]
):
    """Пример эндпоинта, доступного только админам."""
    return {"message": f"Welcome to the Admin Dashboard, {admin_user.user}!"}

# Маршрут для постов
@app.post("/posts", response_model=schemas.Post, tags=["Posts"], status_code=status.HTTP_201_CREATED)
async def create_new_post(
    post_data: schemas.PostCreate, # Данные поста из тела запроса, валидируются Pydantic
    db: AsyncSession = Depends(get_db),
    current_user: schemas.UserBase = Depends(auth.get_current_user) # Получаем текущего пользователя
):
    try:
         
        """ Создает новый пост.
        Пользователь должен быть аутентифицирован.
        """
    # Вызываем CRUD функцию для создания поста в БД
    # Передаем данные поста и имя текущего пользователя как владельца
    # current_user.user - это поле с уникальным именем пользователя из вашей схемы UserCurrent
    # которое должно соответствовать User.user и Post.post_owner_user_fk
        created_post_db = await posts.create_post(db=db, post=post_data, owner_user=current_user.user)

    # FastAPI автоматически преобразует объект SQLAlchemy 'created_post_db' (models.Post)
    # в схему 'schemas.PostDisplay' для ответа клиенту.
    # Это работает благодаря `response_model=schemas.PostDisplay` и `from_attributes=True` в схеме.
    # Pydantic схема PostDisplay ожидает атрибут owner_user, который является объектом User.
    # В нашей модели Post есть relationship owner_user, который уже загружен (lazy="selectin")
    # или будет загружен при обращении.
        return created_post_db
    except Exception as e:
        # Логирование ошибки
        print(f"Error in endpoint /users/post: {e}")
        # Если create_post уже обработал ошибку БД и перевыбросил ее,
        # то здесь можно просто вернуть HTTP 500 или более специфичную ошибку.
        # Если create_post не перевыбрасывает, то нужно обработать здесь.
        # Пример: если create_post может выбросить кастомное исключение
        # if isinstance(e, MyCustomDbError):
        #     raise HTTPException(status_code=400, detail=str(e))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An internal error occurred: {str(e)}")
@app.get("/{post_id}/post", response_model=schemas.PostGetAll, tags=["Posts"], status_code=status.HTTP_201_CREATED)
async def get_post_by_post_id(
    post_id: int, 
    db: AsyncSession = Depends(get_db) 
):
    get_post = await posts.get_post_by_id(post_id=post_id, db=db)
    return get_post
@app.get("/{post_id}/posts", response_model=List[schemas.Post], tags=["Posts"], status_code=status.HTTP_201_CREATED)
async def get_posts_from_owner_endpoint(
    post_user: Annotated[models.User, Depends(auth.get_current_user)],
    db: AsyncSession = Depends(get_db),
    skip: int = 0, limit: int = 100,
    
):
    get_posts = await posts.get_posts_from_owner(db=db, post_user=post_user.user, skip=skip, limit=limit)
    return get_posts

@app.get("/posts", response_model=List[schemas.PostGetAll], tags=["Posts"], status_code=status.HTTP_201_CREATED)
async def get_posts_endpoint(
    db: AsyncSession = Depends(get_db),
    skip: int = 0, limit: int = 100,
):
    get_posts = await posts.get_posts(db=db, skip=skip, limit=limit)
    return get_posts
         
@app.post("/{post_id}/members", response_model=schemas.Post, tags=["Posts"], status_code=status.HTTP_201_CREATED)
async def add_post_member_endpoint(
    member_data: Annotated[models.User, Depends(auth.get_current_user)],
    post_id: int,
    db: AsyncSession = Depends(get_db),

):
    try:
        updated_post = await posts.add_member_to_post( # posts - это ваш модуль с функцией
            db=db,
            post_id=post_id,
            username_to_add=member_data.user
        )
        return updated_post
    except HTTPException as e: # Перехватываем HTTPException, выброшенные из posts
        raise e # И просто перевыбрасываем их, FastAPI их обработает
    except Exception as e: # Другие неожиданные ошибки
        # Логируем e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
# Get enum dictionary 
@app.delete("/{post_id}/post", response_model=schemas.Message, tags=["Posts"], status_code=status.HTTP_201_CREATED)
async def delete_post_by_id(
    member_data: Annotated[models.User, Depends(auth.get_current_user)],
    post_id: int,
    db: AsyncSession = Depends(get_db),
):
    await posts.delete_post_by_id(db=db, post_id=post_id, user=member_data)
    return {"message": "Post deleted succesful"}

@app.get("/capitals-for-select", response_model=List[schemas.SelectOption], tags=["Enums"])
async def get_capitals_for_select_options():
    """
    Возвращает список столиц в формате, подходящем для HTML <select> или аналогичных UI компонентов.
    Каждый элемент списка - это объект с полями 'value' и 'label'.
    """
    options_list = [
        schemas.SelectOption(value=member.value, label=member.name.title())
        for member in CountriesCapitals
    ]
    return options_list
@app.get("/permissions-for-select", response_model=List[schemas.SelectOption], tags=["Enums"])
async def get_permissions_for_select_options():
    """
    Возвращает список столиц в формате, подходящем для HTML <select> или аналогичных UI компонентов.
    Каждый элемент списка - это объект с полями 'value' и 'label'.
    """
    options_list = [
        schemas.SelectOption(value=member.value, label=member.name.title())
        for member in UserRole
    ]
    return options_list

@app.get("/protected", summary="Example protected endpoint", response_model=schemas.Message, tags=["Login system"])
async def protected_route(
    current_user: Annotated[models.User, Depends(auth.get_current_user)]
):
    """Пример эндпоинта, доступного только авторизованным пользователям."""
    return {"message": f"Hello {current_user.user}! You have access."}

@app.get("/", summary="Public root endpoint", response_model=schemas.Message, tags=["Login system"])
async def read_root():
    """Корневой эндпоинт, доступный всем."""
    return {"message": "Welcome to the Cookie Auth API!"}

# --- Event Handlers ---
@app.on_event("startup")
async def startup_event():
    """
    Run database migrations on startup.
    Note: In production, use Alembic or similar for migrations.
    """
    print("Starting up...")
    await create_tables()
    print("Database tables checked/created.")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Clean up resources on shutdown.
    """
    print("Shutting down...")
    # You might close the engine pool here if necessary,
    # though uvicorn handles process termination gracefully.
    await engine.dispose() # Example: Close the engine pool

@app.post("/users/", response_model=schemas.User, status_code=status.HTTP_201_CREATED, tags=["Users"]) # Указываем модель ответа
async def create_api_user(user_data: schemas.UserCreate, # Получаем данные из тела запроса
                           db: AsyncSession = Depends(get_db) # Получаем сессию БД
):
    # Проверяем, существует ли пользователь с таким email или именем
    db_user_by_email = await crud.get_user_by_email(db, email=user_data.email)
    if db_user_by_email:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user_by_name = await crud.get_user_by_username(db, username=user_data.user)
    if db_user_by_name:
        raise HTTPException(status_code=400, detail="Username already registered")

    try:
        # Вызываем функцию CRUD для создания пользователя
        created_user = await crud.create_user(db=db, user=user_data)
        return created_user # FastAPI автоматически преобразует в JSON по схеме User
    except ValueError as e: # Ловим ошибку из CRUD, если пользователь уже существует
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Ловим другие возможные ошибки из CRUD
        print(f"Непредвиденная ошибка в API при создании пользователя: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during user creation")

@app.get("/users/", response_model=List[schemas.User], tags=["Users"])
async def read_all_user(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """
    Retrieve all users with pagination.
    """
    users = await crud.get_users(db, skip=skip, limit=limit)
    return users

@app.post("/users/{user_id}", response_model=schemas.Item, status_code=status.HTTP_201_CREATED, tags=["Users"]) # Указываем модель ответа
async def create_api_user_shopping_cart(user_id: int, user_data: schemas.ItemBase, # Получаем данные из тела запроса
                           db: AsyncSession = Depends(get_db) # Получаем сессию БД
):
    db_user = await crud.get_user_by_id(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    try:
        # Вызываем функцию CRUD для создания пользователя
        created_item: models.Item | None = await crud.create_shoping_card_item(id=user_id , db=db, item=user_data)
    # --- КОНЕЦ ПРОВЕРКИ ---
        return created_item # FastAPI автоматически преобразует в JSON по схеме User
    except ValueError as e: # Ловим ошибку из CRUD, если пользователь уже существует
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Ловим другие возможные ошибки из CRUD
        print(f"Непредвиденная ошибка в API при создании пользователя: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during user creation")

@app.get("/users/{user_id}", response_model=schemas.User, tags=["Users"])
async def read_single_user(user_id: Annotated[models.User, Depends(auth.get_current_user)], db: AsyncSession = Depends(get_db)):
    """
    Retrieve a single user by its ID.
    """
 
    db_user = await crud.get_user_by_id(db, user_id=user_id.id)
    print(f"DEBUG: CRUD function returned: {db_user!r}") # <--- ДОБАВЬТЕ ЭТО
    # print(f"DEBUG: Type of returned object: {type(created_item)}") # <--- И ЭТО
    if db_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    print(f"DEBUG: Returning User object: {db_user!r}")
    try:
        # --- ПОПЫТКА ЯВНОГО ПРЕОБРАЗОВАНИЯ В PYDANTIC СХЕМУ ---
        print("DEBUG: Attempting manual Pydantic validation/serialization...")

        # Используем model_validate (для Pydantic V2) для создания
        # экземпляра схемы User из объекта SQLAlchemy User.
        # Это должно использовать from_attributes=True рекурсивно.
        pydantic_user = schemas.User.model_validate(db_user)

        print(f"DEBUG: Pydantic model created successfully: {pydantic_user!r}")
        # Если мы дошли сюда, Pydantic смог обработать объект.
        # Возвращаем созданный Pydantic объект, а не ORM объект.
        return pydantic_user
        return db_user
    except ValidationError as e:
        # Если Pydantic сам вызвал ошибку валидации
        print(f"ERROR: Pydantic ValidationError during manual validation: {e.json()}") # Выводим детали ошибки Pydantic
        raise HTTPException(
            status_code=500,
            detail=f"Pydantic validation failed during response generation: {e}"
        )
    except Exception as e:
        # Другие ошибки при попытке преобразования
        print(f"ERROR: Unexpected error during manual validation/serialization: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error during response generation: {e}"
        )

@app.put("/users/{user_id}", response_model=schemas.User, tags=["Users"])
async def update_existing_user(user_id: int, user_update: schemas.UserBase, db: AsyncSession = Depends(get_db)):
    """
    Update an existing user by its ID.
    Only updates fields provided in the request body.
    """
    updated_user = await crud.update_user(db=db, user_id=user_id, user_update=user_update)
    if updated_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return updated_user

@app.delete("/users/{user_id}", response_model=schemas.User, tags=["Users"])
# Use status code 200 OK or 204 No Content for successful deletion
# If returning the deleted item, 200 OK is appropriate.
async def delete_existing_user(user_id: int, db: AsyncSession = Depends(get_db)):
    """
    Delete an user by its ID.
    """
    deleted_user = await crud.delete_user(db=db, user_id=user_id)
    if deleted_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return deleted_user # Or return {"message": "Item deleted successfully"} with status_code=200