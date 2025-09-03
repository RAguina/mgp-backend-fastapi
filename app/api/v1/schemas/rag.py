# backend/app/api/v1/schemas/rag.py
"""
RAG Schemas para soportar el workflow: Create → Manage → Use
Compatible con la UI del frontend implementada
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any, Literal
from enum import Enum


class RAGStatus(str, Enum):
    """Estados del procesamiento RAG"""
    CREATING = "creating"       # Creando estructura inicial
    PROCESSING = "processing"   # Procesando documentos (chunking, embedding)
    READY = "ready"            # Listo para usar
    ERROR = "error"            # Error en procesamiento
    DELETED = "deleted"        # Marcado como eliminado


class RAGProcessingStep(str, Enum):
    """Pasos del procesamiento RAG"""
    UPLOADING = "uploading"         # Subiendo archivos
    EXTRACTING = "extracting"       # Extrayendo texto
    CHUNKING = "chunking"          # Dividiendo en chunks
    EMBEDDING = "embedding"        # Generando embeddings
    INDEXING = "indexing"          # Indexando en vector store
    COMPLETED = "completed"        # Completado


# ===== REQUEST SCHEMAS =====

class RAGCreateRequest(BaseModel):
    """Request para crear un nuevo RAG workspace"""
    name: str = Field(..., min_length=1, max_length=100, description="Nombre del RAG workspace")
    description: Optional[str] = Field(None, max_length=500, description="Descripción opcional")
    
    # Configuración de procesamiento
    embedding_model: str = Field("bge-m3", description="Modelo de embeddings a usar")
    vector_store: str = Field("milvus", description="Base de datos vectorial")
    
    # Configuración avanzada
    chunk_size: Optional[int] = Field(512, ge=64, le=2048, description="Tamaño de chunks")
    chunk_overlap: Optional[int] = Field(50, ge=0, le=256, description="Overlap entre chunks")
    
    # Metadatos opcionales
    tags: Optional[List[str]] = Field([], description="Tags para organización")
    is_public: Optional[bool] = Field(False, description="Si es público o privado")


class RAGUploadRequest(BaseModel):
    """Request para subir documentos a un RAG existente"""
    rag_id: str = Field(..., description="ID del RAG workspace")
    # Los archivos se manejan como UploadFile en el endpoint


class RAGConfigureRequest(BaseModel):
    """Request para configurar RAG para uso en chat"""
    rag_id: str = Field(..., description="ID del RAG workspace a usar")
    
    # Configuración de retrieval
    top_k: Optional[int] = Field(5, ge=1, le=20, description="Número de documentos a recuperar")
    similarity_threshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="Umbral de similitud")
    
    # Configuración avanzada de búsqueda
    search_strategy: Optional[str] = Field("semantic", description="Estrategia de búsqueda")
    rerank: Optional[bool] = Field(False, description="Aplicar re-ranking")


# ===== RESPONSE SCHEMAS =====

class RAGMetrics(BaseModel):
    """Métricas del RAG workspace"""
    total_documents: int = Field(0, description="Total de documentos")
    total_chunks: int = Field(0, description="Total de chunks")
    total_embeddings: int = Field(0, description="Total de embeddings")
    storage_size_mb: float = Field(0.0, description="Tamaño en MB")
    processing_time_sec: Optional[float] = Field(None, description="Tiempo de procesamiento")
    last_updated: Optional[datetime] = Field(None, description="Última actualización")


class RAGProcessingStatus(BaseModel):
    """Estado detallado del procesamiento"""
    current_step: RAGProcessingStep
    progress_percent: float = Field(0.0, ge=0.0, le=100.0)
    current_file: Optional[str] = None
    total_files: int = 0
    processed_files: int = 0
    estimated_time_remaining: Optional[int] = None  # segundos
    error_message: Optional[str] = None


class RAGDocument(BaseModel):
    """Información de un documento en el RAG"""
    id: str
    filename: str
    file_type: str  # "pdf", "txt", "docx", etc.
    file_size_mb: float
    upload_date: datetime
    status: Literal["uploaded", "processed", "error"]
    chunk_count: Optional[int] = None
    error_message: Optional[str] = None


class RAGWorkspace(BaseModel):
    """RAG Workspace completo"""
    id: str
    name: str
    description: Optional[str] = None
    status: RAGStatus
    
    # Configuración
    embedding_model: str
    vector_store: str
    chunk_size: int
    chunk_overlap: int
    
    # Metadatos
    tags: List[str] = []
    is_public: bool = False
    created_at: datetime
    updated_at: datetime
    
    # Estado y métricas
    processing_status: Optional[RAGProcessingStatus] = None
    metrics: RAGMetrics
    
    # Documentos (opcional, solo si se solicita)
    documents: Optional[List[RAGDocument]] = None


class RAGWorkspaceList(BaseModel):
    """Lista paginada de RAG workspaces"""
    workspaces: List[RAGWorkspace]
    total: int
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    has_prev: bool = False


# ===== SUCCESS RESPONSES =====

class RAGCreateResponse(BaseModel):
    """Respuesta de creación exitosa"""
    success: bool = True
    message: str = "RAG workspace created successfully"
    rag_id: str
    workspace: RAGWorkspace


class RAGUploadResponse(BaseModel):
    """Respuesta de upload exitoso"""
    success: bool = True
    message: str = "Files uploaded successfully"
    uploaded_files: List[str]
    processing_started: bool = True


class RAGDeleteResponse(BaseModel):
    """Respuesta de eliminación exitosa"""
    success: bool = True
    message: str = "RAG workspace deleted successfully"
    deleted_rag_id: str


# ===== ERROR RESPONSES =====

class RAGErrorResponse(BaseModel):
    """Respuesta de error estándar"""
    success: bool = False
    error_type: str  # "validation", "not_found", "processing", "server"
    message: str
    details: Optional[Dict[str, Any]] = None


# ===== CONFIGURATION SCHEMAS =====

class EmbeddingModelConfig(BaseModel):
    """Configuración específica de modelo de embedding"""
    name: str
    provider: str  # "huggingface", "openai", "cohere"
    model_path: Optional[str] = None
    api_key: Optional[str] = None
    dimensions: int
    max_tokens: int
    batch_size: Optional[int] = 32


class VectorStoreConfig(BaseModel):
    """Configuración específica de vector store"""
    name: str
    provider: str  # "milvus", "weaviate", "pinecone", "chroma"
    connection_params: Dict[str, Any]
    collection_name: Optional[str] = None
    index_config: Optional[Dict[str, Any]] = None


class RAGSystemConfig(BaseModel):
    """Configuración general del sistema RAG"""
    available_embedding_models: List[EmbeddingModelConfig]
    available_vector_stores: List[VectorStoreConfig]
    default_embedding_model: str = "bge-m3"
    default_vector_store: str = "milvus"
    max_file_size_mb: int = 100
    supported_file_types: List[str] = ["pdf", "txt", "docx", "md"]
    max_documents_per_rag: int = 1000