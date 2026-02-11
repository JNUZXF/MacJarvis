# File: backend/app/infrastructure/database/models.py
# Purpose: SQLAlchemy ORM models for database tables
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey, Index
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime
from typing import Optional

Base = declarative_base()


class User(Base):
    """User model for storing user information and relationships"""
    __tablename__ = "users"
    
    id = Column(String(36), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Memory fields - simplified text storage
    memory_preferences = Column(Text, default='', nullable=False)  # User preferences
    memory_facts = Column(Text, default='', nullable=False)  # Objective facts about user
    memory_episodes = Column(Text, default='', nullable=False)  # Important conversation episodes
    memory_tasks = Column(Text, default='', nullable=False)  # Ongoing tasks and work state
    memory_relations = Column(Text, default='', nullable=False)  # Relationships between entities
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    paths = relationship("UserPath", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<User(id={self.id})>"


class Session(Base):
    """Session model for chat sessions"""
    __tablename__ = "sessions"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan", order_by="Message.created_at")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_user_id', 'user_id'),
        Index('idx_session_updated_at', 'updated_at'),
        Index('idx_session_user_updated', 'user_id', 'updated_at'),
    )
    
    def __repr__(self):
        return f"<Session(id={self.id}, title={self.title})>"


class Message(Base):
    """Message model for chat messages"""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system, tool
    content = Column(Text)
    tool_calls = Column(JSON)  # Store tool calls as JSON
    tool_call_results = Column(JSON)  # Store tool call results as JSON
    message_metadata = Column(JSON)  # Store additional metadata (timestamps, etc.) - renamed from 'metadata' to avoid SQLAlchemy conflict
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    session = relationship("Session", back_populates="messages")

    # Indexes
    __table_args__ = (
        Index('idx_message_session_id', 'session_id'),
        Index('idx_message_created_at', 'created_at'),
        Index('idx_message_session_created', 'session_id', 'created_at'),
    )

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"


class UserPath(Base):
    """User path model for storing allowed file system paths"""
    __tablename__ = "user_paths"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    path = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="paths")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_path_user_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<UserPath(user_id={self.user_id}, path={self.path})>"


class UploadedFile(Base):
    """Model for tracking uploaded files"""
    __tablename__ = "uploaded_files"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(256), nullable=False)
    content_type = Column(String(128))
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Indexes
    __table_args__ = (
        Index('idx_uploaded_file_user_id', 'user_id'),
        Index('idx_uploaded_file_created_at', 'created_at'),
    )

    def __repr__(self):
        return f"<UploadedFile(id={self.id}, filename={self.filename})>"


class DelegatedTask(Base):
    """Model for tracking delegated background tasks"""
    __tablename__ = "delegated_tasks"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)

    # Task information
    task_description = Column(Text, nullable=False)  # Task description from user
    context = Column(JSON, nullable=True)  # Additional context (chat history, etc.)

    # Status tracking
    status = Column(String(20), nullable=False, default='pending')  # pending, running, completed, failed
    celery_task_id = Column(String(100), nullable=True)  # Celery task ID for tracking

    # Results and error tracking
    result = Column(Text, nullable=True)  # Task result/output
    error = Column(Text, nullable=True)  # Error message if failed

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    started_at = Column(DateTime, nullable=True)  # When task started running
    completed_at = Column(DateTime, nullable=True)  # When task completed/failed

    # Notification tracking
    notified = Column(Integer, default=0, nullable=False)  # Whether user has been notified (0=no, 1=yes)

    # Indexes
    __table_args__ = (
        Index('idx_delegated_task_user_id', 'user_id'),
        Index('idx_delegated_task_session_id', 'session_id'),
        Index('idx_delegated_task_status', 'status'),
        Index('idx_delegated_task_notified', 'notified'),
        Index('idx_delegated_task_created_at', 'created_at'),
        Index('idx_delegated_task_user_status', 'user_id', 'status'),
    )

    def __repr__(self):
        return f"<DelegatedTask(id={self.id}, status={self.status}, description={self.task_description[:50]}...)>"


