# app/api/v1/routes/execute.py

from fastapi import APIRouter, HTTPException
from app.api.v1.schemas.execution import ExecutionRequest, ExecutionResult
from app.services.executor import execute_prompt

router = APIRouter()


@router.post("/execute", response_model=ExecutionResult)
async def handle_execute(request: ExecutionRequest):
    """
    Ruta principal de ejecución de prompts.
    Llama al servicio del laboratorio y retorna la respuesta.
    """
    try:
        # Ejecutar prompt (ahora es async)
        result = await execute_prompt(request)
        
        # Ya no necesitas crear ExecutionResult aquí,
        # execute_prompt ya retorna un ExecutionResult completo
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))