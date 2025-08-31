# backend/app/services/executor.py
"""
Servicio ejecutor actualizado para manejar simple vs orchestrator
MANTIENE INDEPENDENCIA ARQUITECTURAL - No imports directos del lab
"""

import httpx
import uuid
import logging
import time
from datetime import datetime
from typing import Dict, Any

from app.api.v1.schemas.execution import ExecutionRequest, ExecutionResult
from app.api.v1.schemas.types import FlowState, NodeState, Edge, ExecutionMetrics

# Configuración del Lab API (MANTENER IGUAL)
LAB_API_URL = "http://127.0.0.1:8001"
REQUEST_TIMEOUT = 300.0  # 5 minutos para modelos pesados

logger = logging.getLogger(__name__)


async def execute_prompt(request: ExecutionRequest) -> ExecutionResult:
    """
    ✅ FUNCIÓN PRINCIPAL ACTUALIZADA
    Ejecuta el prompt usando simple LLM u orchestrator según execution_type
    """
    execution_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Log del tipo de ejecución
    logger.info(f"[{execution_id}] Execution type: {request.execution_type}")
    logger.info(f"[{execution_id}] Prompt: {request.prompt[:100]}...")
    
    try:
        if request.execution_type == "orchestrator":
            # ✅ CORRECTO: Llamada API al lab (como simple)
            result = await _execute_orchestrator_via_api(request, execution_id)
            
        elif request.execution_type == "simple":
            # ✅ EXISTENTE: Usar tu código actual (mantener funcionando)
            result = await _execute_simple_llm(request, execution_id)
            
        else:
            raise ValueError(f"Unknown execution_type: {request.execution_type}")
        
        total_time = time.time() - start_time
        logger.info(f"[{execution_id}] Completed in {total_time:.2f}s")
        
        return ExecutionResult(
            id=execution_id,
            timestamp=datetime.utcnow(),
            prompt=request.prompt,
            output=result["output"],
            execution_type=request.execution_type,
            flow=result["flow"],
            metrics=result["metrics"]
        )
        
    except Exception as e:
        logger.error(f"[{execution_id}] Failed: {str(e)}")
        
        # Fallback error response
        return ExecutionResult(
            id=execution_id,
            timestamp=datetime.utcnow(),
            prompt=request.prompt,
            output=f"Error en ejecución: {str(e)}",
            execution_type=request.execution_type,
            flow=FlowState(nodes=[], edges=[], current_node=None),
            metrics=ExecutionMetrics(
                total_time=time.time() - start_time,
                tokens_generated=0,
                models_used=[request.model or "unknown"]
            )
        )


async def _execute_orchestrator_via_api(request: ExecutionRequest, execution_id: str) -> Dict[str, Any]:
    """
    ✅ CORRECTO: Ejecuta orchestrator via API call al lab (independiente)
    """
    logger.info(f"[{execution_id}] Using orchestrator via lab API")
    logger.info(f"[{execution_id}] Agents: {request.agents}")
    logger.info(f"[{execution_id}] Tools: {request.tools}")
    
    try:
        # ✅ NUEVO ENDPOINT: Necesitarás agregarlo al lab
        orchestrator_payload = {
            "prompt": request.prompt,
            "model": request.model,
            "execution_type": "orchestrator",
            "agents": request.agents or [],
            "tools": request.tools or [],
            "verbose": request.verbose,
            "enable_history": request.enable_history,
            "retry_on_error": request.retry_on_error
        }
        
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            # Health check primero
            health_response = await client.get(f"{LAB_API_URL}/health")
            if health_response.status_code != 200:
                raise Exception("Lab service not available")
            
            logger.info(f"[{execution_id}] Calling lab orchestrator endpoint")
            
            # ✅ NUEVO: Llamada al endpoint /orchestrate (pendiente crear en lab)
            response = await client.post(
                f"{LAB_API_URL}/orchestrate",  # ✅ NUEVO ENDPOINT
                json=orchestrator_payload,
                timeout=REQUEST_TIMEOUT
            )
            
            if response.status_code != 200:
                raise Exception(f"Lab orchestrator error: {response.status_code}")
            
            lab_result = response.json()
        
        # Verificar que la respuesta sea exitosa
        if not lab_result.get('success', False):
            raise Exception("Lab orchestrator execution was not successful")
        
        # Convertir respuesta del lab al formato del backend
        flow = create_flow_from_orchestrator_response(lab_result)
        metrics = create_metrics_from_orchestrator_response(lab_result)
        
        logger.info(f"[{execution_id}] Orchestrator completed via API")
        
        return {
            "output": lab_result.get('output', 'No output received'),
            "flow": flow,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"[{execution_id}] Orchestrator API failed: {str(e)}")
        raise


async def _execute_simple_llm(request: ExecutionRequest, execution_id: str) -> Dict[str, Any]:
    """
    ✅ FUNCIÓN ADAPTADA: Tu código actual adaptado para el nuevo flujo
    """
    logger.info(f"[{execution_id}] Using simple LLM via lab service")
    
    try:
        # ✅ USAR TU LÓGICA ACTUAL (check_lab_health, call_lab_inference, etc.)
        
        # Verificar que el lab esté disponible
        if not await check_lab_health():
            raise Exception("Lab API is not available")
        
        # Llamar al lab usando TU función existente
        lab_response = await call_lab_inference(request)
        
        # Verificar que la respuesta sea exitosa
        if not lab_response.get('success', False):
            raise Exception("Lab execution was not successful")
        
        # ✅ USAR TUS FUNCIONES ACTUALES
        flow = create_flow_from_lab_response(lab_response)
        metrics = create_execution_metrics(lab_response)
        
        logger.info(f"[{execution_id}] Simple LLM completed")
        
        return {
            "output": lab_response.get('output', 'No output received'),
            "flow": flow,
            "metrics": metrics
        }
        
    except Exception as e:
        logger.error(f"[{execution_id}] Simple LLM failed: {str(e)}")
        raise


def create_flow_from_orchestrator_response(lab_response: Dict[str, Any]) -> FlowState:
    """
    ✅ NUEVA: Convierte respuesta del orchestrator en FlowState
    """
    # El lab debería retornar algo como:
    # {
    #   "flow": {
    #     "nodes": [...],
    #     "edges": [...]
    #   }
    # }
    
    flow_data = lab_response.get('flow', {})
    nodes_data = flow_data.get('nodes', [])
    edges_data = flow_data.get('edges', [])
    
    # Convertir nodos
    flow_nodes = []
    for node_data in nodes_data:
        flow_nodes.append(NodeState(
            id=node_data.get("id", "unknown"),
            name=node_data.get("name", "Unknown Worker"),
            type=node_data.get("type", "worker"),
            status=node_data.get("status", "completed"),
            start_time=node_data.get("start_time", 0),
            end_time=node_data.get("end_time", 0),
            output=node_data.get("output", ""),
            error=node_data.get("error", None)
        ))
    
    # Convertir edges
    flow_edges = []
    for edge_data in edges_data:
        flow_edges.append(Edge(
            source=edge_data.get("source", ""),
            target=edge_data.get("target", ""),
            label=edge_data.get("label", None)
        ))
    
    return FlowState(
        nodes=flow_nodes,
        edges=flow_edges,
        current_node=flow_nodes[-1].id if flow_nodes else None
    )


def create_metrics_from_orchestrator_response(lab_response: Dict[str, Any]) -> ExecutionMetrics:
    """
    ✅ NUEVA: Convierte métricas del orchestrator al formato del backend
    """
    metrics_data = lab_response.get('metrics', {})
    
    return ExecutionMetrics(
        total_time=metrics_data.get('total_time', 0.0),
        tokens_generated=metrics_data.get('tokens_generated', 0),
        models_used=metrics_data.get('models_used', ['unknown'])
    )


# ✅ MANTENER TODAS TUS FUNCIONES ACTUALES (sin cambios)
async def check_lab_health() -> bool:
    """
    Verifica que el Lab API esté disponible.
    """
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{LAB_API_URL}/health")
            return response.status_code == 200
    except Exception as e:
        logger.error(f"Lab API health check failed: {e}")
        return False


async def get_available_models() -> Dict[str, str]:
    """
    Obtiene los modelos disponibles del Lab API.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LAB_API_URL}/models")
            response.raise_for_status()
            
            models = response.json()
            return {model["key"]: model["name"] for model in models}
    except Exception as e:
        logger.error(f"Failed to get models from lab: {e}")
        return {}


async def call_lab_inference(request: ExecutionRequest) -> Dict[str, Any]:
    """
    Llama al Lab API para ejecutar inferencia.
    """
    payload = {
        "prompt": request.prompt,
        "model": request.model,
        "strategy": request.strategy,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature
    }
    
    logger.info(f"Calling lab inference: model={request.model}, strategy={request.strategy}")
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{LAB_API_URL}/inference/",
                json=payload
            )
            response.raise_for_status()
            return response.json()
            
    except httpx.TimeoutException:
        logger.error("Lab API request timed out")
        raise Exception("Model execution timed out")
    except httpx.HTTPStatusError as e:
        logger.error(f"Lab API returned error {e.response.status_code}: {e.response.text}")
        raise Exception(f"Lab API error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"Unexpected error calling lab: {e}")
        raise Exception(f"Failed to connect to lab: {str(e)}")


def create_flow_from_lab_response(lab_response: Dict[str, Any]) -> FlowState:
    """
    Convierte la respuesta del lab en un FlowState para el frontend.
    """
    model_node = NodeState(
        id="model_execution",
        name=f"Model: {lab_response.get('model', 'unknown')}",
        type="llm_inference",
        status="completed",
        start_time=0.0,
        end_time=lab_response.get('metrics', {}).get('execution_time', 0.0),
        output=lab_response.get('output', ''),
        error=None
    )
    
    return FlowState(
        nodes=[model_node],
        edges=[],
        current_node=None
    )


def create_execution_metrics(lab_response: Dict[str, Any]) -> ExecutionMetrics:
    """
    Convierte las métricas del lab al formato del backend.
    """
    lab_metrics = lab_response.get('metrics', {})
    
    return ExecutionMetrics(
        total_time=lab_metrics.get('total_time_sec', 0.0),
        tokens_generated=lab_metrics.get('tokens_generated'),
        models_used=[lab_response.get('model', 'unknown')]
    )


# ✅ MANTENER función de testing actualizada
async def test_lab_connection():
    """
    Función para probar la conexión con el lab.
    """
    try:
        health = await check_lab_health()
        models = await get_available_models()
        
        # ✅ Test del nuevo endpoint de orchestrator
        orchestrator_available = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{LAB_API_URL}/api/orchestrate")
                orchestrator_available = response.status_code in [200, 405]  # 405 = Method not allowed (pero existe)
        except:
            pass
        
        return {
            "lab_healthy": health,
            "available_models": models,
            "lab_url": LAB_API_URL,
            "orchestrator_endpoint_available": orchestrator_available
        }
    except Exception as e:
        return {
            "lab_healthy": False,
            "error": str(e),
            "lab_url": LAB_API_URL,
            "orchestrator_endpoint_available": False
        }