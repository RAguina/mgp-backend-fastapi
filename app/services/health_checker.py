# app/services/health_checker.py
"""
Servicio para verificar el estado del sistema.
Centraliza la lógica de health checks y evita acoplamiento con lógica de ejecución.
Separado completamente de ExecutionMetrics y FlowState.
"""

import time
from typing import Dict, Tuple


class HealthChecker:
    """
    Servicio centralizado para health checks del sistema.
    🎯 Enfoque: Infraestructura y disponibilidad, NO métricas de ejecución de IA.
    """
    
    def __init__(self):
        self.start_time = time.time()
    
    def get_uptime(self) -> int:
        """Calcula el uptime en segundos desde el inicio del servicio"""
        return int(time.time() - self.start_time)
    
    async def check_components(self) -> Dict[str, str]:
        """
        Verifica el estado de componentes del sistema.
        Retorna un diccionario con el estado de cada componente.
        
        📝 Nota: Separado de ExecutionMetrics - esto es infraestructura, no IA.
        """
        components = {
            "api": "healthy",
            "fastapi": "healthy"
        }
        
        # 🔮 Futuras verificaciones (sin acoplar con execution logic):
        # - Redis connection: await self._check_redis()
        # - PostgreSQL connection: await self._check_database()
        # - External services: await self._check_external_apis()
        # - File system: await self._check_storage()
        # 
        # ❌ NO incluir aquí:
        # - GPU model loading (eso es responsabilidad de executor.py)
        # - LangGraph state (eso es responsabilidad de FlowState)
        # - Token generation metrics (eso es ExecutionMetrics)
        
        return components
    
    async def check_readiness(self) -> Tuple[bool, Dict[str, str]]:
        """
        Verifica si el servicio está listo para recibir requests.
        Retorna (is_ready, dependencies_status).
        
        🎯 Enfoque: Dependencias críticas para que la API funcione.
        """
        dependencies = {
            "fastapi": "ready",
            "python_runtime": "ready"
        }
        
        # 🔮 Futuras verificaciones críticas:
        # - Database connection pool
        # - Redis pub/sub connection  
        # - Essential config values loaded
        # - Required directories/files accessible
        #
        # ❌ NO verificar aquí:
        # - Si los modelos están cargados (eso lo maneja el executor)
        # - Si hay prompts en cola (eso es lógica de negocio)
        
        # Por ahora, siempre ready (agregar lógica según necesidades)
        is_ready = all(status == "ready" for status in dependencies.values())
        
        return is_ready, dependencies