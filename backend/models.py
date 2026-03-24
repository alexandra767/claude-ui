from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime, timezone
import uuid


def new_id():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=new_id)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    display_name = Column(String, default="")
    avatar_url = Column(String, default="")
    theme = Column(String, default="system")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, default="New conversation")
    model = Column(String, default="qwen3.5:122b")
    project_id = Column(String, ForeignKey("projects.id"), nullable=True)
    is_starred = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="conversations")
    project = relationship("Project", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")


class Message(Base):
    __tablename__ = "messages"
    id = Column(String, primary_key=True, default=new_id)
    conversation_id = Column(String, ForeignKey("conversations.id"), nullable=False)
    role = Column(String, nullable=False)  # user, assistant, system, tool
    content = Column(Text, default="")
    model = Column(String, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    tool_results = Column(JSON, nullable=True)
    artifacts = Column(JSON, nullable=True)  # [{id, type, title, content}]
    attachments = Column(JSON, nullable=True)  # [{filename, path, type, size}]
    token_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    conversation = relationship("Conversation", back_populates="messages")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=new_id)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, default="")
    system_prompt = Column(Text, default="")
    color = Column(String, default="#DA7756")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    user = relationship("User", back_populates="projects")
    conversations = relationship("Conversation", back_populates="project")
    files = relationship("ProjectFile", back_populates="project", cascade="all, delete-orphan")


class ProjectFile(Base):
    __tablename__ = "project_files"
    id = Column(String, primary_key=True, default=new_id)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    file_type = Column(String, default="")
    file_size = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    project = relationship("Project", back_populates="files")
