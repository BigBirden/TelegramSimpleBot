
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, Enum, ForeignKey, DateTime
from enum import Enum as PyEnum
from datetime import datetime

from app.db import Base

class UserRole(PyEnum):
    ADMIN = "admin"
    USER = "user"
    # Добавьте другие роли по необходимости

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(50))
    last_name: Mapped[str] = mapped_column(String(50), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.USER)
    
    messages = relationship("Message", back_populates="user")
    dialogs = relationship("DialogUser", back_populates="user")
    
class Dialog(Base):
    __tablename__ = "dialogs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    messages = relationship("Message", back_populates="dialog")
    users = relationship("DialogUser", back_populates="dialog")

class DialogUser(Base):
    __tablename__ = "dialog_users"
    
    dialog_id: Mapped[int] = mapped_column(Integer, ForeignKey("dialogs.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), primary_key=True)
    
    dialog = relationship("Dialog", back_populates="users")
    user = relationship("User", back_populates="dialogs")
    
class Message(Base):
    __tablename__ = "messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"))
    dialog_id: Mapped[int] = mapped_column(Integer, ForeignKey("dialogs.id"))
    
    user = relationship("User", back_populates="messages")
    dialog = relationship("Dialog", back_populates="messages")