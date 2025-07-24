# app/main.py

import logging
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routes.execute import router as execute_router
from app.api.v1.routes.health import router as health_router
from app.core.config import settings

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger("uvicorn")

# Inicializar FastAPI
app = FastAPI(
    title="AI Agent Lab - Backend API",
    version="0.1.0",
    description="Capa de orquestación REST para ejecución de prompts vía LangGraph",
)

# Configurar CORS (ajustar en producción)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cambiar por dominios específicos en prod
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rutas (health primero para máxima eficiencia)
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(execute_router, prefix="/api/v1", tags=["Execution"])

# Eventos de ciclo de vida
@app.on_event("startup")
async def on_startup():
    app.state.ready = True
    app.state.start_time = time.time()  # Para tracking de uptime
    logger.info("✅ API FastAPI inicializada correctamente.")

@app.on_event("shutdown")
async def on_shutdown():
    app.state.ready = False
    logger.info("⛔ API FastAPI detenida.")