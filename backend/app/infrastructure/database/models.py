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
    
    # Relationships
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    paths = relationship("UserPath", back_populates="user", cascade="all, delete-orphan")
    episodes = relationship("EpisodicMemory", back_populates="user", cascade="all, delete-orphan")
    semantic_memories = relationship("SemanticMemory", back_populates="user", cascade="all, delete-orphan")
    
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
    metadata = Column(JSON)  # Store additional metadata (timestamps, etc.)
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


class EpisodicMemory(Base):
    """Episodic memory model for storing conversation episodes"""
    __tablename__ = "episodic_memory"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), nullable=True)
    episode_type = Column(String(50), nullable=False)  # conversation, summary, task, etc.
    summary = Column(Text, nullable=False)
    content = Column(JSON, nullable=False)  # Full episode content
    metadata = Column(JSON)  # Additional metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="episodes")
    
    # Indexes
    __table_args__ = (
        Index('idx_episodic_user_id', 'user_id'),
        Index('idx_episodic_session_id', 'session_id'),
        Index('idx_episodic_created_at', 'created_at'),
        Index('idx_episodic_user_created', 'user_id', 'created_at'),
    )
    
    def __repr__(self):
        return f"<EpisodicMemory(id={self.id}, type={self.episode_type})>"


class SemanticMemory(Base):
    """Semantic memory model for storing knowledge with embeddings"""
    __tablename__ = "semantic_memory"
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=False)  # Vector embedding as JSON array
    metadata = Column(JSON)  # Source, tags, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="semantic_memories")
    
    # Indexes
    __table_args__ = (
        Index('idx_semantic_user_id', 'user_id'),
        Index('idx_semantic_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<SemanticMemory(id={self.id}, user_id={self.user_id})>"


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
