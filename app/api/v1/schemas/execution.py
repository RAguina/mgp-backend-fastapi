# backend/app/api/v1/schemas/execution.py
"""
Esquemas actualizados para soportar orquestador y simple LLM
MANTIENE COMPATIBILIDAD con frontend existente
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Literal

from .types import FlowState, ExecutionMetrics


class ExecutionRequest(BaseModel):
    prompt: str = Field(..., description="Prompt enviado por el usuario")
    model: Optional[str] = Field("mistral7b", description="Modelo a usar")
    
    # ✅ NUEVO: Diferenciador de tipo de ejecución (DEFAULT = "simple")
    execution_type: Literal["simple", "orchestrator", "challenge"] = Field(
        "simple", 
        description="Tipo de ejecución: simple (LLM directo), orchestrator (LangGraph) o challenge (flujo avanzado)"
    )
    
    # ✅ RAG FIELDS: Pass-through opcionales para el Lab
    embedding_model: Optional[str] = Field(
        None, 
        description="Modelo de embeddings para RAG",
        examples=["bge-m3", "e5-large", "openai-embed"]
    )
    vector_store: Optional[str] = Field(
        None,
        description="Base de datos vectorial para RAG", 
        examples=["milvus", "weaviate", "pinecone"]
    )
    rag_config: Optional[dict] = Field(
        None,
        description="Configuración específica de RAG",
        examples=[{"top_k": 5, "threshold": 0.7, "chunk_size": 512}]
    )
    
    # Campos para simple LLM (MANTIENEN compatibilidad)
    strategy: Optional[str] = Field("optimized", description="Estrategia de ejecución")
    temperature: Optional[float] = Field(0.7, ge=0, le=1, description="Temperatura del modelo")
    max_tokens: Optional[int] = Field(512, ge=16, le=4096, description="Tokens máximos")
    
    # ✅ NUEVO: Campos para orchestrator (TODOS OPCIONALES)
    agents: Optional[List[str]] = Field(
        None, 
        description="Lista de agentes a usar (para orchestrator)",
        examples=[["research_agent", "knowledge_agent"]]
    )
    tools: Optional[List[str]] = Field(
        None,
        description="Lista de herramientas disponibles (para orchestrator)",
        examples=[["web_search", "wikipedia", "calculator"]]
    )
    
    # Configuración avanzada (opcional)
    verbose: Optional[bool] = Field(False, description="Logging detallado")
    enable_history: Optional[bool] = Field(True, description="Incluir historial")
    retry_on_error: Optional[bool] = Field(True, description="Reintentar en caso de error")
    flow_type: Optional[str] = Field(None, description="Tipo de flujo (para challenge)")


class ExecutionResult(BaseModel):
    id: str
    timestamp: datetime
    prompt: str
    output: str
    execution_type: str  # ✅ NUEVO: Incluir tipo de ejecución en respuesta
    flow: FlowState
    metrics: ExecutionMetrics