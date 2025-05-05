# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship, declarative_base
from database import Base# Import Base from our database setup
from sqlalchemy.sql import func
import datetime

class Item(Base):
    __tablename__ = "items" # The actual table name in the database

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, index=True, nullable=True)
    price = Column(Float, nullable=False)
    # Add other columns as needed
 # ВНЕШНИЙ КЛЮЧ: Указывает на ID пользователя-владельца
    owner_id = Column(Integer, ForeignKey("users.id")) # "users.id" - имя_таблицы.имя_столбца

    # ОПРЕДЕЛЕНИЕ СВЯЗИ "МНОГИЕ-КО-ОДНОМУ"
    # 'User' - Имя класса на "одной" стороне.
    # back_populates='items' - Связывает это поле с полем 'items' в модели User.
    owner = relationship("User", back_populates="items", lazy="selectin")
    def __repr__(self):
        return (f"<Item(id={self.id}, name='{self.name}', price={self.price}, "
                f"owner_id={self.owner_id})>")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user = Column(String, unique=True)  #  Уникальное имя пользователя
    password = Column(String)
    email = Column(String, unique=True)  # Уникальный email
 # ОПРЕДЕЛЕНИЕ СВЯЗИ "ОДИН-КО-МНОГИМ"
    # 'Item' - Имя класса на "множественной" стороне.
    # back_populates='owner' - Связывает это поле с полем 'owner' в модели Item.
    #                       Обеспечивает двунаправленную связь.
    # lazy='selectin' (опционально) - Стратегия загрузки связанных объектов.
    #                         'selectin' обычно эффективнее для async.
    items = relationship("Item", back_populates="owner",  cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<User(id={self.id}, user='{self.user}', email='{self.email}')>"
    
# class DenylistedToken(Base):
#     __tablename__ = 'denylisted_tokens'

#     # Using String for JTI as UUIDs are often represented as strings
#     jti = Column(String, primary_key=True, index=True)
#     # Store the original expiry time of the token for cleanup purposes
#     # Use timezone=True to ensure timezone awareness
#     expires_at = Column(DateTime(timezone=True), nullable=False)

#     def __repr__(self):
#         return f"<DenylistedToken(jti='{self.jti}', expires_at='{self.expires_at}')>"