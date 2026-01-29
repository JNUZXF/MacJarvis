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
    preferences = relationship("PreferenceMemory", back_populates="user", cascade="all, delete-orphan")
    facts = relationship("FactMemory", back_populates="user", cascade="all, delete-orphan")
    tasks = relationship("TaskMemory", back_populates="user", cascade="all, delete-orphan")
    relations = relationship("RelationMemory", back_populates="user", cascade="all, delete-orphan")
    
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


class PreferenceMemory(Base):
    """Preference memory model for storing user preferences"""
    __tablename__ = "preference_memory"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    category = Column(String(100), nullable=False)  # food, communication, work, etc.
    preference_key = Column(String(200), nullable=False)  # dietary_restriction, response_style, etc.
    preference_value = Column(Text, nullable=False)  # vegetarian, concise, etc.
    confidence = Column(Integer, default=5, nullable=False)  # 1-10 scale
    source = Column(String(100))  # explicit, inferred, etc.
    metadata = Column(JSON)  # Additional context
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_confirmed_at = Column(DateTime)  # When user last confirmed this preference

    # Relationships
    user = relationship("User", back_populates="preferences")

    # Indexes
    __table_args__ = (
        Index('idx_pref_user_id', 'user_id'),
        Index('idx_pref_category', 'category'),
        Index('idx_pref_user_category', 'user_id', 'category'),
        Index('idx_pref_key', 'user_id', 'preference_key'),
    )

    def __repr__(self):
        return f"<PreferenceMemory(id={self.id}, key={self.preference_key}, value={self.preference_value})>"


class FactMemory(Base):
    """Fact memory model for storing objective facts about the user"""
    __tablename__ = "fact_memory"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    fact_type = Column(String(100), nullable=False)  # personal, professional, family, etc.
    subject = Column(String(200), nullable=False)  # name, job_title, location, etc.
    fact_value = Column(Text, nullable=False)  # The actual fact
    confidence = Column(Integer, default=5, nullable=False)  # 1-10 scale
    source = Column(String(100))  # direct_statement, inferred, etc.
    metadata = Column(JSON)  # Related entities, timestamps, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    verified_at = Column(DateTime)  # When this fact was last verified

    # Relationships
    user = relationship("User", back_populates="facts")

    # Indexes
    __table_args__ = (
        Index('idx_fact_user_id', 'user_id'),
        Index('idx_fact_type', 'fact_type'),
        Index('idx_fact_user_type', 'user_id', 'fact_type'),
        Index('idx_fact_subject', 'user_id', 'subject'),
    )

    def __repr__(self):
        return f"<FactMemory(id={self.id}, subject={self.subject}, value={self.fact_value})>"


class TaskMemory(Base):
    """Task memory model for storing ongoing tasks and work state"""
    __tablename__ = "task_memory"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    session_id = Column(String(36), nullable=True)  # Associated session if any
    task_type = Column(String(100), nullable=False)  # project, todo, goal, etc.
    title = Column(String(500), nullable=False)
    description = Column(Text)
    status = Column(String(50), nullable=False, default='active')  # active, completed, cancelled, on_hold
    progress = Column(Integer, default=0)  # 0-100 percentage
    priority = Column(String(20), default='medium')  # low, medium, high, urgent
    context = Column(JSON)  # Related files, links, dependencies, etc.
    metadata = Column(JSON)  # Tags, labels, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    due_date = Column(DateTime)
    completed_at = Column(DateTime)

    # Relationships
    user = relationship("User", back_populates="tasks")

    # Indexes
    __table_args__ = (
        Index('idx_task_user_id', 'user_id'),
        Index('idx_task_status', 'status'),
        Index('idx_task_user_status', 'user_id', 'status'),
        Index('idx_task_session_id', 'session_id'),
        Index('idx_task_updated', 'updated_at'),
    )

    def __repr__(self):
        return f"<TaskMemory(id={self.id}, title={self.title}, status={self.status})>"


class RelationMemory(Base):
    """Relation memory model for storing relationships between entities"""
    __tablename__ = "relation_memory"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_entity = Column(String(200), nullable=False)  # Entity A
    subject_type = Column(String(100), nullable=False)  # person, project, organization, etc.
    relation_type = Column(String(100), nullable=False)  # is_manager_of, works_on, belongs_to, etc.
    object_entity = Column(String(200), nullable=False)  # Entity B
    object_type = Column(String(100), nullable=False)  # person, project, organization, etc.
    confidence = Column(Integer, default=5, nullable=False)  # 1-10 scale
    bidirectional = Column(Integer, default=0, nullable=False)  # 0 or 1 (SQLite doesn't have boolean)
    metadata = Column(JSON)  # Context, properties, etc.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="relations")

    # Indexes
    __table_args__ = (
        Index('idx_rel_user_id', 'user_id'),
        Index('idx_rel_subject', 'user_id', 'subject_entity'),
        Index('idx_rel_object', 'user_id', 'object_entity'),
        Index('idx_rel_type', 'relation_type'),
        Index('idx_rel_entities', 'subject_entity', 'object_entity'),
    )

    def __repr__(self):
        return f"<RelationMemory(id={self.id}, {self.subject_entity} {self.relation_type} {self.object_entity})>"
