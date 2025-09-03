# backend/app/api/v1/routes/rag.py
"""
RAG CRUD endpoints para soportar el workflow del frontend:
Create → Manage → Use
"""

import logging
import os
import shutil
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.v1.schemas.rag import (
    RAGCreateRequest, RAGCreateResponse,
    RAGUploadRequest, RAGUploadResponse, 
    RAGDeleteResponse, RAGErrorResponse,
    RAGWorkspace, RAGWorkspaceList, RAGDocument,
    RAGProcessingStatus, RAGMetrics,
    RAGStatus, RAGProcessingStep
)
from app.db.models import (
    RAGWorkspace as RAGWorkspaceModel,
    RAGDocument as RAGDocumentModel,
    RAGProcessingLog as RAGProcessingLogModel,
    get_workspace_by_id, update_workspace_metrics
)
from app.core.database import get_db
from app.services.rag_processor import start_document_processing

logger = logging.getLogger(__name__)

router = APIRouter()

# Configuración
UPLOAD_DIR = "uploads/rag"
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
ALLOWED_FILE_TYPES = {".pdf", ".txt", ".docx", ".md"}

# Crear directorio de uploads si no existe
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ===== UTILITY FUNCTIONS =====

def convert_db_workspace_to_schema(db_workspace: RAGWorkspaceModel, include_documents: bool = False) -> RAGWorkspace:
    """
    Convierte modelo de DB a schema de respuesta
    """
    # Obtener último estado de procesamiento
    processing_status = None
    if db_workspace.processing_logs:
        latest_log = max(db_workspace.processing_logs, key=lambda x: x.started_at)
        processing_status = RAGProcessingStatus(
            current_step=RAGProcessingStep(latest_log.step),
            progress_percent=latest_log.progress_percent,
            current_file=latest_log.current_file,
            total_files=latest_log.total_files,
            processed_files=latest_log.processed_files,
            estimated_time_remaining=latest_log.estimated_time_remaining,
            error_message=latest_log.error_message
        )
    
    # Métricas
    metrics = RAGMetrics(
        total_documents=db_workspace.total_documents,
        total_chunks=db_workspace.total_chunks,
        total_embeddings=db_workspace.total_embeddings,
        storage_size_mb=db_workspace.storage_size_mb,
        processing_time_sec=db_workspace.processing_time_sec,
        last_updated=db_workspace.updated_at
    )
    
    # Documentos (opcional)
    documents = None
    if include_documents:
        documents = [
            RAGDocument(
                id=doc.id,
                filename=doc.original_filename,
                file_type=doc.file_type,
                file_size_mb=doc.file_size_mb,
                upload_date=doc.upload_date,
                status=doc.status,
                chunk_count=doc.chunk_count,
                error_message=doc.error_message
            )
            for doc in db_workspace.documents
        ]
    
    return RAGWorkspace(
        id=db_workspace.id,
        name=db_workspace.name,
        description=db_workspace.description,
        status=RAGStatus(db_workspace.status),
        embedding_model=db_workspace.embedding_model,
        vector_store=db_workspace.vector_store,
        chunk_size=db_workspace.chunk_size,
        chunk_overlap=db_workspace.chunk_overlap,
        tags=db_workspace.tags or [],
        is_public=db_workspace.is_public,
        created_at=db_workspace.created_at,
        updated_at=db_workspace.updated_at,
        processing_status=processing_status,
        metrics=metrics,
        documents=documents
    )


# ===== CRUD ENDPOINTS =====

@router.post("/create", response_model=RAGCreateResponse)
async def create_rag_workspace(request: RAGCreateRequest, db: Session = Depends(get_db)):
    """
    Crear un nuevo RAG workspace
    Frontend: RAG Workspace → Create Tab
    """
    try:
        logger.info(f"Creating RAG workspace: {request.name}")
        
        # Crear workspace en DB
        db_workspace = RAGWorkspaceModel(
            name=request.name,
            description=request.description,
            status="creating",
            embedding_model=request.embedding_model,
            vector_store=request.vector_store,
            chunk_size=request.chunk_size,
            chunk_overlap=request.chunk_overlap,
            tags=request.tags,
            is_public=request.is_public
        )
        
        db.add(db_workspace)
        db.commit()
        db.refresh(db_workspace)
        
        # Crear directorio para archivos
        workspace_dir = os.path.join(UPLOAD_DIR, db_workspace.id)
        os.makedirs(workspace_dir, exist_ok=True)
        
        logger.info(f"RAG workspace created: {db_workspace.id}")
        
        workspace_schema = convert_db_workspace_to_schema(db_workspace)
        
        return RAGCreateResponse(
            rag_id=db_workspace.id,
            workspace=workspace_schema
        )
        
    except Exception as e:
        logger.error(f"Error creating RAG workspace: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create RAG workspace: {str(e)}")


@router.get("/list", response_model=RAGWorkspaceList)
async def list_rag_workspaces(
    page: int = 1,
    per_page: int = 20,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Listar RAG workspaces
    Frontend: RAG Workspace → Manage Tab
    """
    try:
        # Query base
        query = db.query(RAGWorkspaceModel).filter(RAGWorkspaceModel.status != "deleted")
        
        # Filtro por status
        if status_filter:
            query = query.filter(RAGWorkspaceModel.status == status_filter)
        
        # Paginación
        total = query.count()
        workspaces = query.order_by(RAGWorkspaceModel.updated_at.desc()).offset((page - 1) * per_page).limit(per_page).all()
        
        # Convertir a schema
        workspace_schemas = [convert_db_workspace_to_schema(ws) for ws in workspaces]
        
        return RAGWorkspaceList(
            workspaces=workspace_schemas,
            total=total,
            page=page,
            per_page=per_page,
            has_next=(page * per_page) < total,
            has_prev=page > 1
        )
        
    except Exception as e:
        logger.error(f"Error listing RAG workspaces: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list workspaces: {str(e)}")


@router.get("/{workspace_id}", response_model=RAGWorkspace)
async def get_rag_workspace(workspace_id: str, include_documents: bool = False, db: Session = Depends(get_db)):
    """
    Obtener detalles de un RAG workspace específico
    Frontend: RAG Workspace → Manage Tab → View details
    """
    try:
        db_workspace = get_workspace_by_id(db, workspace_id)
        if not db_workspace or db_workspace.status == "deleted":
            raise HTTPException(status_code=404, detail="RAG workspace not found")
        
        workspace_schema = convert_db_workspace_to_schema(db_workspace, include_documents=include_documents)
        return workspace_schema
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting RAG workspace {workspace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get workspace: {str(e)}")


@router.post("/{workspace_id}/upload", response_model=RAGUploadResponse)
async def upload_documents(
    workspace_id: str,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Subir documentos a un RAG workspace
    Frontend: RAG Workspace → Create Tab → Upload PDFs
    """
    try:
        # Verificar que el workspace existe
        db_workspace = get_workspace_by_id(db, workspace_id)
        if not db_workspace or db_workspace.status == "deleted":
            raise HTTPException(status_code=404, detail="RAG workspace not found")
        
        if db_workspace.status not in ["creating", "ready"]:
            raise HTTPException(status_code=400, detail="Workspace is not ready for uploads")
        
        uploaded_files = []
        workspace_dir = os.path.join(UPLOAD_DIR, workspace_id)
        
        for file in files:
            # Validaciones
            if file.size > MAX_FILE_SIZE:
                raise HTTPException(status_code=400, detail=f"File {file.filename} is too large")
            
            file_ext = os.path.splitext(file.filename)[1].lower()
            if file_ext not in ALLOWED_FILE_TYPES:
                raise HTTPException(status_code=400, detail=f"File type {file_ext} not supported")
            
            # Guardar archivo
            file_id = str(uuid.uuid4())
            file_path = os.path.join(workspace_dir, f"{file_id}{file_ext}")
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            # Crear registro en DB
            db_document = RAGDocumentModel(
                workspace_id=workspace_id,
                filename=f"{file_id}{file_ext}",
                original_filename=file.filename,
                file_type=file_ext[1:],  # Sin el punto
                file_size_mb=file.size / (1024 * 1024),
                file_path=file_path,
                status="uploaded"
            )
            
            db.add(db_document)
            uploaded_files.append(file.filename)
        
        # Actualizar estado del workspace
        db_workspace.status = "processing"
        db_workspace.updated_at = datetime.utcnow()
        
        db.commit()
        
        # Iniciar procesamiento en background
        background_tasks.add_task(start_document_processing, workspace_id, db)
        
        logger.info(f"Uploaded {len(uploaded_files)} files to workspace {workspace_id}")
        
        return RAGUploadResponse(
            uploaded_files=uploaded_files,
            processing_started=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading files to workspace {workspace_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to upload files: {str(e)}")


@router.delete("/{workspace_id}", response_model=RAGDeleteResponse)
async def delete_rag_workspace(workspace_id: str, db: Session = Depends(get_db)):
    """
    Eliminar un RAG workspace
    Frontend: RAG Workspace → Manage Tab → Delete
    """
    try:
        db_workspace = get_workspace_by_id(db, workspace_id)
        if not db_workspace or db_workspace.status == "deleted":
            raise HTTPException(status_code=404, detail="RAG workspace not found")
        
        # Marcar como eliminado (soft delete)
        db_workspace.status = "deleted"
        db_workspace.updated_at = datetime.utcnow()
        
        # TODO: Limpiar archivos físicos y vector store en background
        
        db.commit()
        
        logger.info(f"Deleted RAG workspace: {workspace_id}")
        
        return RAGDeleteResponse(deleted_rag_id=workspace_id)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting RAG workspace {workspace_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete workspace: {str(e)}")


@router.post("/{workspace_id}/duplicate", response_model=RAGCreateResponse)
async def duplicate_rag_workspace(workspace_id: str, new_name: str = Form(...), db: Session = Depends(get_db)):
    """
    Duplicar un RAG workspace
    Frontend: RAG Workspace → Manage Tab → Duplicate
    """
    try:
        # Obtener workspace original
        original_workspace = get_workspace_by_id(db, workspace_id)
        if not original_workspace or original_workspace.status == "deleted":
            raise HTTPException(status_code=404, detail="RAG workspace not found")
        
        # Crear nuevo workspace con la misma configuración
        db_workspace = RAGWorkspaceModel(
            name=new_name,
            description=f"Copy of {original_workspace.name}",
            status="creating",
            embedding_model=original_workspace.embedding_model,
            vector_store=original_workspace.vector_store,
            chunk_size=original_workspace.chunk_size,
            chunk_overlap=original_workspace.chunk_overlap,
            tags=original_workspace.tags,
            is_public=original_workspace.is_public
        )
        
        db.add(db_workspace)
        db.commit()
        db.refresh(db_workspace)
        
        # Crear directorio
        workspace_dir = os.path.join(UPLOAD_DIR, db_workspace.id)
        os.makedirs(workspace_dir, exist_ok=True)
        
        # TODO: Copiar documentos en background si se requiere
        
        logger.info(f"Duplicated RAG workspace {workspace_id} to {db_workspace.id}")
        
        workspace_schema = convert_db_workspace_to_schema(db_workspace)
        
        return RAGCreateResponse(
            message="RAG workspace duplicated successfully",
            rag_id=db_workspace.id,
            workspace=workspace_schema
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating RAG workspace {workspace_id}: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to duplicate workspace: {str(e)}")


# ===== STATUS AND MONITORING =====

@router.get("/{workspace_id}/status", response_model=RAGProcessingStatus)
async def get_processing_status(workspace_id: str, db: Session = Depends(get_db)):
    """
    Obtener estado de procesamiento en tiempo real
    Frontend: Polling para actualizar progress bars
    """
    try:
        db_workspace = get_workspace_by_id(db, workspace_id)
        if not db_workspace:
            raise HTTPException(status_code=404, detail="RAG workspace not found")
        
        # Obtener último log de procesamiento
        latest_log = db.query(RAGProcessingLogModel).filter(
            RAGProcessingLogModel.workspace_id == workspace_id
        ).order_by(RAGProcessingLogModel.started_at.desc()).first()
        
        if not latest_log:
            # No hay procesamiento activo
            status = RAGProcessingStatus(
                current_step=RAGProcessingStep.COMPLETED,
                progress_percent=100.0 if db_workspace.status == "ready" else 0.0
            )
        else:
            status = RAGProcessingStatus(
                current_step=RAGProcessingStep(latest_log.step),
                progress_percent=latest_log.progress_percent,
                current_file=latest_log.current_file,
                total_files=latest_log.total_files,
                processed_files=latest_log.processed_files,
                estimated_time_remaining=latest_log.estimated_time_remaining,
                error_message=latest_log.error_message
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing status for {workspace_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get processing status: {str(e)}")


import uuid  # Necesario para los imports