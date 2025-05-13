# schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator, model_validator, Field
from typing import Optional, List, Any
from enums import CountriesCapitals, UserRole
from exceptrions import wrong_trip_place
# --- Pydantic Schemas ---

# --- Posts Schemas ---
class PostBase(BaseModel):
    post_owner_user: str
    post_id:int
    model_config = ConfigDict(from_attributes=True)
class PostOwnerDisplay(BaseModel):
    post_id:int
    model_config = ConfigDict(from_attributes=True)
class PostCreate(BaseModel):
    trip_from: CountriesCapitals
    trip_to: CountriesCapitals
    count_of_places: int = Field(
        default=1, # Значение по умолчанию, если клиент не передаст
        ge=1,      # ge = greater than or equal (больше или равно) - минимальное количество мест
        le=100,     # le = less than or equal (меньше или равно) - максимальное количество мест
        description="Количество доступных мест в поездке (от 1 до 100)"
    )
    @field_validator('count_of_places')
    @classmethod # Обязательно для field_validator
    def check_count_of_places_range(cls, value: int) -> int:
        # value - это значение, которое уже прошло базовую проверку типа (что это int)
        # и стандартные валидаторы Field (ge, le, если они там есть и не вызвали ошибку ранее)
        min_places = 1
        max_places = 100 # Вы можете вынести эти значения в конфигурацию или константы
        
        if not (min_places <= value <= max_places):
            raise ValueError(f"Количество мест должно быть в диапазоне от {min_places} до {max_places}.")
        return value # Всегда возвращайте значение, если оно валидно

    model_config = ConfigDict(from_attributes=True)
    @model_validator(mode='after') # 'after' означает, что валидатор сработает после валидации отдельных полей
    def check_locations_are_different(cls, values: Any) -> Any:
        # 'values' будет объектом модели после инициализации с данными
        # или словарем, если вы используете model_dump() перед этим, но здесь это сама модель
        trip_from_val = values.trip_from
        trip_to_val = values.trip_to

        if trip_from_val is not None and trip_to_val is not None: # Проверяем, что оба значения не None
            if trip_from_val == trip_to_val:
                raise wrong_trip_place
                # Вместо ValueError можно выбросить кастомное исключение,
                # которое FastAPI затем преобразует в HTTP 422 с нужным сообщением.
                # FastAPI хорошо обрабатывает ValueError из валидаторов Pydantic.
        return values # Важно вернуть объект values (или его измененную версию)
    
class Post(PostCreate):
    already_engaged: int
    model_config = ConfigDict(from_attributes=True)
class PostMemberUserSchema(BaseModel):
    # Эта схема будет представлять пользователя В КОНТЕКСТЕ членства в посте
    member_user: str # Имя пользователя
    post_id: int
    model_config = ConfigDict(from_attributes=True) # Для Pydantic V2
class PostGetAllMemberUserSchema(BaseModel):
    member_user: str # Имя пользователя
    model_config = ConfigDict(from_attributes=True) # Для Pydantic V2
class PostGetAll(Post):
    post_id:int
    post_owner_user: str
    posts_members_posts: List[PostGetAllMemberUserSchema] = []
    model_config = ConfigDict(from_attributes=True)


class PostMemberCreate(BaseModel):
    # post_id_fk и member_user_fk будут предоставлены в эндпоинте
    pass # Пустая, так как ключи будут параметрами пути/тела запроса
# Base schema for common attributes
class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    
# Schema for creating an item (inherits from Base, no id needed)

class Item(ItemBase):
    owner_id: int
    model_config = ConfigDict(from_attributes=True)
    # class Config:
    #     orm_mode = True # Enable Pydantic to work with ORM objects    
class UserBase(BaseModel):
    user: str
    email: EmailStr
    role: UserRole
class UserCreate(UserBase):
    password: str
class User(UserBase): # Схема для ответа API (без пароля)
    id: int
    items: List[Item] = []
    posts_members: List[PostMemberUserSchema] = []
    owned_posts: List[PostOwnerDisplay] = []
    model_config = ConfigDict(from_attributes=True)
    # class Config:
    #     orm_mode = True
# Schema for updating an item (all fields optional)
class ItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None

class UserPublic(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Message(BaseModel):
    message: str
    
class SelectOption(BaseModel):
    value: str  # Значение, которое будет отправляться на сервер
    label: str  # Текст, который будет видеть пользователь