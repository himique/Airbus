import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import  Depends, HTTPException, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, Optional
from depencies import get_db
import models
from enums import UserRole
import crud
import exceptrions
from jose import JWTError, jwt
from passlib.context import CryptContext
from dotenv import load_dotenv


from passlib.context import CryptContext # Для хеширования пароля

load_dotenv()

ACCESS_TOKEN_COOKIE_NAME = "auth_token"
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 1 # 1 часов

if not SECRET_KEY:
    raise ValueError("SECRET_KEY не установлена в .env")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str)-> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет пароль по хешу."""
    return pwd_context.verify(plain_password, hashed_password)

# --- Работа с JWT ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создает JWT токен."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)}) # Добавляем время выдачи
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token_payload(token: str) -> Optional[dict]:
    """
    Декодирует токен и возвращает его payload (содержимое).
    Возвращает None, если токен невалиден или истек.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        # Проверяем наличие обязательного поля 'sub' (subject)
        if "sub" not in payload:
             return None
        return payload
    except JWTError: # Ловит ExpiredSignatureError, JWTClaimsError, и др.
        return None
    
async def get_token_from_cookie(
    token: Annotated[Optional[str], Cookie(alias=ACCESS_TOKEN_COOKIE_NAME)] = None
) -> Optional[str]:
    """Извлекает токен из cookie. Возвращает None, если cookie отсутствует."""
    return token

async def get_current_user(
    token: Annotated[Optional[str], Depends(get_token_from_cookie)],
    db: Annotated[AsyncSession, Depends(get_db)]
) -> models.User:
    """
    Проверяет токен из cookie и возвращает объект пользователя из БД.
    Вызывает HTTPException 401, если аутентификация не удалась.
    """
  
    if token is None:
        # print("Authentication failed: Cookie not found") # Отладка
        raise exceptrions.credentials_exception

    payload = decode_token_payload(token)
    if payload is None:
        # print("Authentication failed: Invalid or expired token") # Отладка
        raise exceptrions.credentials_exception

    username: Optional[str] = payload.get("sub") # 'sub' - стандартное поле для subject (username)
    if username is None:
        # print("Authentication failed: Token payload missing 'sub'") # Отладка
        raise exceptrions.credentials_exception

    user = await crud.get_user_by_username(db, username=username)
    if user is None:
        # print(f"Authentication failed: User '{username}' not found in DB") # Отладка
        raise exceptrions.credentials_exception

    # Можно добавить проверку активности пользователя: if not user.is_active: raise ...
    # print(f"Authentication successful for user: {user.username} (ID: {user.id})") # Отладка
    return user

async def require_admin_user(
    # Сначала получаем текущего аутентифицированного пользователя
    current_user: Annotated[models.User, Depends(get_current_user)]
) -> models.User: # Возвращаем пользователя, если проверка роли прошла
    """ 
    Зависимость: Проверяет, что текущий пользователь аутентифицирован 
    И имеет роль 'admin'. В противном случае вызывает HTTPException 403.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, # !!! 403 Forbidden - доступ запрещен (не 401 Unauthorized)
            detail="Operation not permitted. Administrator privileges required or user are not owner.",
        )
    return current_user # Возвращаем пользователя, если он админ

# async def require_user_privileges(
#     current_user: Annotated[models.User, Depends(get_current_user)]
# ) -> models.User:
#     """
#     Зависимость: Проверяет, что текущий пользователь аутентифицирован
#     И имеет роль 'user' или 'admin'.
#     """
#     # Пример: если бы у нас были еще роли, и мы хотели бы ограничить доступ
#     # if current_user.role not in [models.UserRole.USER, models.UserRole.ADMIN]:
#     #     raise HTTPException(
#     #         status_code=status.HTTP_403_FORBIDDEN,
#     #         detail="Insufficient privileges.",
#     #     )
#     # В текущей ситуации (только User и Admin), get_current_user уже достаточен.
#     # Эта функция здесь больше для иллюстрации.
#     return current_user