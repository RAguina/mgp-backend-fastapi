# app/api/v1/schemas/health.py
"""
Esquemas para health checks y monitoring del sistema.
Separados de los tipos de ejecución para mantener dominios desacoplados.
"""

from datetime import datetime
from typing import Dict, Optional, Literal
from pydantic import BaseModel, Field


class HealthStatus(BaseModel):
    """Respuesta básica de health check - ultra ligera"""
    status: Literal["healthy", "unhealthy"] = "healthy"
    timestamp: datetime
    service: str = Field(default="ai-agent-lab-backend", description="Nombre del servicio")


class DetailedHealthStatus(BaseModel):
    """Health check detallado con verificación de componentes"""
    status: Literal["healthy", "degraded", "unhealthy"] = "healthy"
    timestamp: datetime
    service: str = Field(default="ai-agent-lab-backend", description="Nombre del servicio")
    version: str = Field(default="0.1.0", description="Versión de la API")
    components: Dict[str, str] = Field(description="Estado de componentes del sistema")
    uptime_seconds: Optional[int] = Field(None, description="Tiempo en funcionamiento")


class ReadinessStatus(BaseModel):
    """Estado de readiness - diferente de health/liveness"""
    status: Literal["ready", "not_ready"] = "ready"
    timestamp: datetime
    dependencies: Optional[Dict[str, str]] = Field(None, description="Estado de dependencias críticas")


class SystemMetrics(BaseModel):
    """Métricas de infraestructura del sistema (futuro uso con monitoring)"""
    cpu_usage_percent: Optional[float] = Field(None, ge=0, le=100)
    memory_usage_mb: Optional[int] = Field(None, ge=0)
    active_connections: Optional[int] = Field(None, ge=0)