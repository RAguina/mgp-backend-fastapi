# app/api/v1/routes/execute.py

import logging
from fastapi import APIRouter, HTTPException, Request
from app.api.v1.schemas.execution import ExecutionRequest, ExecutionResult
from app.services.executor import execute_prompt

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/execute", response_model=ExecutionResult)
async def handle_execute(raw_request: Request, request: ExecutionRequest):
    """
    Ruta principal de ejecución de prompts.
    Llama al servicio del laboratorio y retorna la respuesta.
    """
    try:
        # 🔍 DEBUG: Log el request recibido
        body = await raw_request.body()
        logger.info(f"Raw request body: {body.decode('utf-8')}")
        logger.info(f"Parsed request: {request}")
        
        # Ejecutar prompt (ahora es async)
        result = await execute_prompt(request)
        
        # Ya no necesitas crear ExecutionResult aquí,
        # execute_prompt ya retorna un ExecutionResult completo
        return result
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))