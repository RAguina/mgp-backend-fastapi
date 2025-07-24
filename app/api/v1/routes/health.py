# app/api/v1/routes/health.py
"""
Endpoints de health check y monitoring del sistema.
Diseñado para ser ligero y no consumir recursos GPU/CPU innecesarios.
Completamente separado de la lógica de ejecución de prompts.
"""

from datetime import datetime
from fastapi import APIRouter, Depends
from app.api.v1.schemas.health import HealthStatus, DetailedHealthStatus, ReadinessStatus
from app.services.health_checker import HealthChecker

router = APIRouter()


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Health check básico y ultra-rápido.
    Usado por load balancers y monitoring externo.
    ⚡ No realiza verificaciones pesadas - solo confirma que la API responde.
    """
    return HealthStatus(
        timestamp=datetime.utcnow()
    )


@router.get("/health/detailed", response_model=DetailedHealthStatus)
async def detailed_health_check(
    health_checker: HealthChecker = Depends()
):
    """
    Health check detallado con verificación de componentes.
    🔍 Incluye estado de servicios externos si es necesario.
    Útil para debugging y dashboards de monitoreo.
    """
    components = await health_checker.check_components()
    uptime = health_checker.get_uptime()
    
    return DetailedHealthStatus(
        timestamp=datetime.utcnow(),
        components=components,
        uptime_seconds=uptime
    )


@router.get("/ready", response_model=ReadinessStatus)
async def readiness_check(
    health_checker: HealthChecker = Depends()
):
    """
    Readiness probe - verifica si el servicio está listo para recibir tráfico.
    🎯 Diferente de liveness (health) - este verifica dependencias críticas.
    Usado por Kubernetes y orquestadores para traffic routing.
    """
    is_ready, dependencies = await health_checker.check_readiness()
    
    if not is_ready:
        return ReadinessStatus(
            status="not_ready",
            timestamp=datetime.utcnow(),
            dependencies=dependencies
        )
    
    return ReadinessStatus(
        timestamp=datetime.utcnow(),
        dependencies=dependencies
    )