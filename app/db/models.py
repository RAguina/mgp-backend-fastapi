# backend/app/db/models.py
"""
Database models for RAG workspaces and documents
Using SQLAlchemy for compatibility and flexibility
"""

from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

Base = declarative_base()


class RAGWorkspace(Base):
    """
    RAG Workspace - Main container for documents and configuration
    """
    __tablename__ = "rag_workspaces"
    
    # Identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Status
    status = Column(String(20), nullable=False, default="creating", index=True)
    # Status: creating, processing, ready, error, deleted
    
    # Processing configuration
    embedding_model = Column(String(50), nullable=False, default="bge-m3")
    vector_store = Column(String(50), nullable=False, default="milvus")
    chunk_size = Column(Integer, nullable=False, default=512)
    chunk_overlap = Column(Integer, nullable=False, default=50)
    
    # Metadata
    tags = Column(JSON, nullable=True)  # List of strings
    is_public = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Metrics (denormalized for performance)
    total_documents = Column(Integer, nullable=False, default=0)
    total_chunks = Column(Integer, nullable=False, default=0)
    total_embeddings = Column(Integer, nullable=False, default=0)
    storage_size_mb = Column(Float, nullable=False, default=0.0)
    processing_time_sec = Column(Float, nullable=True)
    
    # Relationships
    documents = relationship("RAGDocument", back_populates="workspace", cascade="all, delete-orphan")
    processing_logs = relationship("RAGProcessingLog", back_populates="workspace", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RAGWorkspace(id='{self.id}', name='{self.name}', status='{self.status}')>"


class RAGDocument(Base):
    """
    Individual document within a RAG workspace
    """
    __tablename__ = "rag_documents"
    
    # Identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("rag_workspaces.id"), nullable=False, index=True)
    
    # File information
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)  # User's original filename
    file_type = Column(String(10), nullable=False)  # pdf, txt, docx, etc.
    file_size_mb = Column(Float, nullable=False)
    file_path = Column(String(500), nullable=False)  # Storage path
    
    # Processing status
    status = Column(String(20), nullable=False, default="uploaded", index=True)
    # Status: uploaded, processing, processed, error
    error_message = Column(Text, nullable=True)
    
    # Processing metrics
    chunk_count = Column(Integer, nullable=True)
    processing_time_sec = Column(Float, nullable=True)
    
    # Extracted metadata
    file_metadata = Column(JSON, nullable=True)  # Title, author, pages, etc.
    
    # Timestamps
    upload_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_date = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    workspace = relationship("RAGWorkspace", back_populates="documents")
    chunks = relationship("RAGDocumentChunk", back_populates="document", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<RAGDocument(id='{self.id}', filename='{self.filename}', status='{self.status}')>"


class RAGDocumentChunk(Base):
    """
    Individual chunk of a document (for granular tracking)
    """
    __tablename__ = "rag_document_chunks"
    
    # Identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String(36), ForeignKey("rag_documents.id"), nullable=False, index=True)
    
    # Chunk information
    chunk_index = Column(Integer, nullable=False)  # Order within document
    content_preview = Column(String(200), nullable=False)  # First 200 chars
    chunk_size = Column(Integer, nullable=False)  # Size in characters
    
    # Vector store info
    vector_id = Column(String(100), nullable=True)  # ID in vector store
    embedding_status = Column(String(20), nullable=False, default="pending")
    # Status: pending, embedded, error
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    embedded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationship
    document = relationship("RAGDocument", back_populates="chunks")
    
    def __repr__(self):
        return f"<RAGDocumentChunk(id='{self.id}', document_id='{self.document_id}', index={self.chunk_index})>"


class RAGProcessingLog(Base):
    """
    Processing log for progress tracking and debugging
    """
    __tablename__ = "rag_processing_logs"
    
    # Identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    workspace_id = Column(String(36), ForeignKey("rag_workspaces.id"), nullable=False, index=True)
    
    # Step information
    step = Column(String(20), nullable=False)  # uploading, extracting, chunking, embedding, indexing
    status = Column(String(20), nullable=False)  # started, in_progress, completed, error
    
    # Progress
    progress_percent = Column(Float, nullable=False, default=0.0)
    current_file = Column(String(255), nullable=True)
    total_files = Column(Integer, nullable=False, default=0)
    processed_files = Column(Integer, nullable=False, default=0)
    
    # Timing
    estimated_time_remaining = Column(Integer, nullable=True)  # seconds
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Error info
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)
    
    # Relationship
    workspace = relationship("RAGWorkspace", back_populates="processing_logs")
    
    def __repr__(self):
        return f"<RAGProcessingLog(id='{self.id}', step='{self.step}', status='{self.status}')>"


class RAGConfiguration(Base):
    """
    RAG system configurations (embedding models, vector stores, etc.)
    """
    __tablename__ = "rag_configurations"
    
    # Identification
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    config_type = Column(String(50), nullable=False, index=True)  # embedding_model, vector_store
    name = Column(String(100), nullable=False)
    
    # Configuration
    provider = Column(String(50), nullable=False)
    config_data = Column(JSON, nullable=False)  # Specific configuration
    
    # Status
    is_active = Column(Boolean, nullable=False, default=True)
    is_default = Column(Boolean, nullable=False, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<RAGConfiguration(type='{self.config_type}', name='{self.name}', provider='{self.provider}')>"


# ===== UTILITY FUNCTIONS =====

def create_tables(engine):
    """
    Create all RAG tables in the database
    """
    Base.metadata.create_all(bind=engine)


def get_workspace_by_id(db, workspace_id: str) -> RAGWorkspace:
    """
    Get workspace by ID
    """
    return db.query(RAGWorkspace).filter(RAGWorkspace.id == workspace_id).first()


def get_user_workspaces(db, user_id: str = None, include_public: bool = True):
    """
    Get user workspaces (future: when we add auth)
    For now returns all non-deleted workspaces
    """
    query = db.query(RAGWorkspace).filter(RAGWorkspace.status != "deleted")
    
    if include_public:
        query = query.filter(RAGWorkspace.is_public == True)
    
    return query.order_by(RAGWorkspace.updated_at.desc()).all()


def update_workspace_metrics(db, workspace_id: str):
    """
    Update calculated workspace metrics
    """
    workspace = get_workspace_by_id(db, workspace_id)
    if not workspace:
        return None
    
    # Calculate metrics from documents
    documents = db.query(RAGDocument).filter(RAGDocument.workspace_id == workspace_id).all()
    
    workspace.total_documents = len(documents)
    workspace.storage_size_mb = sum(doc.file_size_mb for doc in documents)
    workspace.total_chunks = sum(doc.chunk_count or 0 for doc in documents)
    
    db.commit()
    return workspace