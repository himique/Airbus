# models.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum 
from sqlalchemy.orm import relationship
from database import Base# Import Base from our database setup
from enums import UserRole, CountriesCapitals


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
    user = Column(String, unique=True, nullable=False)  #  Уникальное имя пользователя
    password = Column(String)
    email = Column(String, unique=True)  # Уникальный email
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
 # ОПРЕДЕЛЕНИЕ СВЯЗИ "ОДИН-КО-МНОГИМ"
    # 'Item' - Имя класса на "множественной" стороне.
    # back_populates='owner' - Связывает это поле с полем 'owner' в модели Item.
    #                       Обеспечивает двунаправленную связь.
    # lazy='selectin' (опционально) - Стратегия загрузки связанных объектов.
    #                         'selectin' обычно эффективнее для async.
    items = relationship("Item", back_populates="owner",  cascade="all, delete-orphan", lazy="selectin")
    owned_posts = relationship("Post", back_populates="owner_user",  cascade="all, delete-orphan", lazy="selectin")
    posts_members = relationship("PostMember", back_populates="user_member_info",  cascade="all, delete-orphan", lazy="selectin")
    def __repr__(self):
        return f"<User(id={self.id}, user='{self.user}', email='{self.email}, role='{self.role}')>"
    
class Post(Base):
    __tablename__ = 'posts'

    post_id = Column(Integer, primary_key=True)
    post_owner_user = Column(String, ForeignKey("users.user"), nullable=False)
    trip_from = Column(Enum(CountriesCapitals), nullable=False)
    trip_to = Column(Enum(CountriesCapitals), nullable=False)
    count_of_places = Column(Integer, default=1, nullable=False)
    already_engaged = Column(Integer, default=0, nullable=False)

    owner_user = relationship("User", foreign_keys=[post_owner_user], back_populates="owned_posts", lazy="selectin")
    member_entries = relationship("PostMember", back_populates="post_info", cascade="all, delete-orphan", lazy="selectin")
    posts_members_posts = relationship("PostMember", back_populates="user_member_info_posts", cascade="all, delete-orphan", lazy="selectin")
    def __repr__(self):
        return f"<Posts(id={self.post_id}, user={self.post_owner_user}, count of places={self.count_of_places}, already engaged={self.already_engaged})>"
    
class PostMember(Base):
    __tablename__ = 'posts_members'
    member_user = Column(String, ForeignKey("users.user"), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.post_id"), primary_key=True)

    user_member_info = relationship("User", foreign_keys=[member_user],back_populates="posts_members", lazy="selectin")
    user_member_info_posts = relationship("Post", back_populates="posts_members_posts", lazy="selectin")
    post_info = relationship("Post", foreign_keys=[post_id], back_populates="member_entries", lazy="selectin")