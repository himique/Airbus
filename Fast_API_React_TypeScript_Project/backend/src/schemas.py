# schemas.py
from pydantic import BaseModel, EmailStr, ConfigDict 
from typing import Optional, List


# --- Pydantic Schemas ---


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
class UserCreate(UserBase):
    password: str
class User(UserBase): # Схема для ответа API (без пароля)
    id: int
    items: List[Item] = []
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