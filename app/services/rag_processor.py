# backend/app/services/rag_processor.py
"""
RAG Document Processing Service
Maneja el procesamiento en background de documentos RAG
"""

import logging
import time
import asyncio
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session

from app.db.models import (
    RAGWorkspace as RAGWorkspaceModel,
    RAGDocument as RAGDocumentModel,
    RAGProcessingLog as RAGProcessingLogModel,
    get_workspace_by_id, update_workspace_metrics
)
from app.api.v1.schemas.rag import RAGProcessingStep

logger = logging.getLogger(__name__)


class RAGProcessor:
    """
    Procesador de documentos RAG
    Maneja todo el pipeline: extract → chunk → embed → index
    """
    
    def __init__(self):
        self.is_processing = {}  # Track de workspaces en procesamiento
    
    async def process_workspace(self, workspace_id: str, db: Session):
        """
        Procesar todos los documentos de un workspace
        """
        try:
            logger.info(f"Starting processing for workspace {workspace_id}")
            self.is_processing[workspace_id] = True
            
            workspace = get_workspace_by_id(db, workspace_id)
            if not workspace:
                raise Exception("Workspace not found")
            
            # Obtener documentos pendientes
            documents = db.query(RAGDocumentModel).filter(
                RAGDocumentModel.workspace_id == workspace_id,
                RAGDocumentModel.status == "uploaded"
            ).all()
            
            if not documents:
                logger.info(f"No documents to process in workspace {workspace_id}")
                self._complete_processing(workspace, db)
                return
            
            total_files = len(documents)
            processed_files = 0
            
            # Procesar cada documento
            for doc in documents:
                try:
                    logger.info(f"Processing document {doc.filename}")
                    
                    # Step 1: Extract text
                    await self._log_step(workspace_id, RAGProcessingStep.EXTRACTING, 
                                       processed_files / total_files * 100, doc.filename, 
                                       total_files, processed_files, db)
                    
                    text_content = await self._extract_text(doc)
                    
                    # Step 2: Chunk text
                    await self._log_step(workspace_id, RAGProcessingStep.CHUNKING,
                                       (processed_files + 0.3) / total_files * 100, doc.filename,
                                       total_files, processed_files, db)
                    
                    chunks = await self._chunk_text(text_content, workspace.chunk_size, workspace.chunk_overlap)
                    
                    # Step 3: Generate embeddings
                    await self._log_step(workspace_id, RAGProcessingStep.EMBEDDING,
                                       (processed_files + 0.6) / total_files * 100, doc.filename,
                                       total_files, processed_files, db)
                    
                    embeddings = await self._generate_embeddings(chunks, workspace.embedding_model)
                    
                    # Step 4: Index in vector store
                    await self._log_step(workspace_id, RAGProcessingStep.INDEXING,
                                       (processed_files + 0.9) / total_files * 100, doc.filename,
                                       total_files, processed_files, db)
                    
                    await self._index_embeddings(embeddings, workspace.vector_store, doc.id)
                    
                    # Actualizar documento
                    doc.status = "processed"
                    doc.chunk_count = len(chunks)
                    doc.processed_date = datetime.utcnow()
                    
                    processed_files += 1
                    
                    logger.info(f"Successfully processed document {doc.filename}")
                    
                except Exception as e:
                    logger.error(f"Error processing document {doc.filename}: {str(e)}")
                    doc.status = "error"
                    doc.error_message = str(e)
            
            # Finalizar procesamiento
            self._complete_processing(workspace, db)
            
        except Exception as e:
            logger.error(f"Error processing workspace {workspace_id}: {str(e)}")
            await self._log_error(workspace_id, str(e), db)
            workspace.status = "error"
            db.commit()
            
        finally:
            self.is_processing[workspace_id] = False
    
    async def _extract_text(self, document: RAGDocumentModel) -> str:
        """
        Extraer texto del documento según su tipo
        """
        # Simulación por ahora - TODO: implementar extractors reales
        await asyncio.sleep(1)  # Simular procesamiento
        
        if document.file_type == "pdf":
            return f"Extracted text from PDF: {document.filename}"
        elif document.file_type == "txt":
            with open(document.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            return f"Extracted text from {document.file_type}: {document.filename}"
    
    async def _chunk_text(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        """
        Dividir texto en chunks
        """
        await asyncio.sleep(0.5)  # Simular procesamiento
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]
            chunks.append(chunk)
            start = end - chunk_overlap
        
        return chunks
    
    async def _generate_embeddings(self, chunks: List[str], embedding_model: str) -> List[dict]:
        """
        Generar embeddings para los chunks
        """
        await asyncio.sleep(2)  # Simular procesamiento pesado
        
        # Simulación - TODO: integrar con Lab Service
        embeddings = []
        for i, chunk in enumerate(chunks):
            embeddings.append({
                "chunk_index": i,
                "chunk_text": chunk,
                "embedding": [0.1] * 768,  # Embedding fake
                "model": embedding_model
            })
        
        return embeddings
    
    async def _index_embeddings(self, embeddings: List[dict], vector_store: str, document_id: str):
        """
        Indexar embeddings en el vector store
        """
        await asyncio.sleep(1)  # Simular indexing
        
        # Simulación - TODO: integrar con vector stores reales
        logger.info(f"Indexed {len(embeddings)} embeddings in {vector_store} for document {document_id}")
    
    async def _log_step(self, workspace_id: str, step: RAGProcessingStep, progress: float, 
                       current_file: str, total_files: int, processed_files: int, db: Session):
        """
        Log del progreso de procesamiento
        """
        log_entry = RAGProcessingLogModel(
            workspace_id=workspace_id,
            step=step.value,
            status="in_progress",
            progress_percent=progress,
            current_file=current_file,
            total_files=total_files,
            processed_files=processed_files,
            estimated_time_remaining=max(0, (total_files - processed_files) * 30)  # 30 seg por archivo
        )
        
        db.add(log_entry)
        db.commit()
        
        logger.info(f"Workspace {workspace_id}: {step.value} - {progress:.1f}% - {current_file}")
    
    async def _log_error(self, workspace_id: str, error_message: str, db: Session):
        """
        Log de error en procesamiento
        """
        log_entry = RAGProcessingLogModel(
            workspace_id=workspace_id,
            step="error",
            status="error",
            progress_percent=0.0,
            error_message=error_message
        )
        
        db.add(log_entry)
        db.commit()
    
    def _complete_processing(self, workspace: RAGWorkspaceModel, db: Session):
        """
        Completar procesamiento del workspace
        """
        workspace.status = "ready"
        workspace.processing_time_sec = 60.0  # TODO: calcular tiempo real
        workspace.updated_at = datetime.utcnow()
        
        # Actualizar métricas
        update_workspace_metrics(db, workspace.id)
        
        # Log final
        final_log = RAGProcessingLogModel(
            workspace_id=workspace.id,
            step=RAGProcessingStep.COMPLETED.value,
            status="completed",
            progress_percent=100.0,
            completed_at=datetime.utcnow()
        )
        
        db.add(final_log)
        db.commit()
        
        logger.info(f"Completed processing for workspace {workspace.id}")


# Instancia global del procesador
processor = RAGProcessor()


def start_document_processing(workspace_id: str, db: Session):
    """
    Función para iniciar procesamiento en background
    """
    try:
        # Ejecutar procesamiento asíncrono
        asyncio.create_task(processor.process_workspace(workspace_id, db))
        logger.info(f"Started background processing for workspace {workspace_id}")
        
    except Exception as e:
        logger.error(f"Error starting background processing: {str(e)}")


async def get_processing_status(workspace_id: str, db: Session) -> Optional[dict]:
    """
    Obtener estado actual de procesamiento
    """
    try:
        latest_log = db.query(RAGProcessingLogModel).filter(
            RAGProcessingLogModel.workspace_id == workspace_id
        ).order_by(RAGProcessingLogModel.started_at.desc()).first()
        
        if not latest_log:
            return None
        
        return {
            "step": latest_log.step,
            "progress": latest_log.progress_percent,
            "current_file": latest_log.current_file,
            "total_files": latest_log.total_files,
            "processed_files": latest_log.processed_files,
            "estimated_remaining": latest_log.estimated_time_remaining,
            "error": latest_log.error_message
        }
        
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        return None


def is_workspace_processing(workspace_id: str) -> bool:
    """
    Verificar si un workspace está en procesamiento
    """
    return processor.is_processing.get(workspace_id, False)