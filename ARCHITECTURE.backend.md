Backend Architecture — AI Agent Lab API Layer
🎯 Objetivo
Exponer una API desacoplada y robusta para conectar el frontend del laboratorio con LangGraph y modelos LLM. Esta capa será responsable de:

Recibir prompts y parámetros desde el frontend

Ejecutar tareas usando el laboratorio (sin bloquear el backend)

Emitir eventos a WebSocket (progreso/output)

Persistir ejecuciones y logs en PostgreSQL

🧰 Stack Tecnológico
FastAPI: Framework principal (ASGI-ready)

Redis: Pub/Sub entre backend y WebSocket

Node.js (opcional): WebSocket server independiente

PostgreSQL: Historial de ejecuciones y métricas

Docker Compose: Entorno completo para despliegue local

🔗 Flujo Principal
mermaid
Copiar
Editar
sequenceDiagram
  participant FE as Frontend
  participant API as FastAPI API
  participant LAB as LangGraph Lab (Python)
  participant REDIS as Redis PubSub
  participant WS as WebSocket Server

  FE->>API: POST /api/execute
  API->>LAB: Ejecutar prompt (background)
  LAB-->>REDIS: Emitir logs/output
  WS-->>FE: Reenviar vía socket
🛡️ Seguridad
CORS + validación con JWT o token

Validación estricta (Pydantic)

Throttling por IP (middleware futuro)

Logging estructurado (por request ID)

📁 Estructura de Carpetas
bash
Copiar
Editar
backend/
├── app/
│   ├── main.py                  # Entrypoint FastAPI
│   ├── api/                     # Endpoints REST
│   │   └── v1/
│   │       ├── routes/
│   │       │   └── execute.py   # POST /api/v1/execute
│   │       ├── schemas/
│   │       │   ├── execution.py # Request/Response para ejecución
│   │       │   └── types.py     # FlowState, ExecutionMetrics, etc.
│   ├── core/                    # Configuración y servicios globales
│   │   ├── config.py            # Lectura de .env, parámetros
│   │   ├── logger.py            # Logging con IDs de request
│   │   └── redis.py             # Cliente de Redis (pub/sub)
│   ├── services/
│   │   └── executor.py          # Invoca LangGraph o modelos locales
│   ├── sockets/
│   │   └── manager.py           # Conexión con WS (opcional)
│   └── db/
│       └── models.py            # ORM/SQL para guardar resultados
├── tests/
│   └── test_execute.py          # Test unitario para POST /execute
├── Dockerfile                   # Imagen base del backend
└── docker-compose.yml           # Orquestador con Redis, Postgres, etc.
📄 Detalles por Módulo
app/api/v1/routes/execute.py
Define el endpoint POST /api/v1/execute

Valida input con ExecutionRequest

Retorna ExecutionResult simulado (por ahora)

En futuro: delega a services.executor.run_execution

app/api/v1/schemas/
execution.py: Define el contrato ExecutionRequest, ExecutionResult

types.py: Define FlowState, NodeState, ExecutionMetrics, etc.

app/core/
config.py: Carga de .env, valores de entorno

logger.py: Inicializa loggers con IDs y timestamps

redis.py: Cliente para publicar eventos (publish_log, publish_output)

app/services/executor.py
Llama al LangGraph Lab local (via subprocess o import)

Simula ejecución en background (futuro: async def run con BackgroundTasks)

app/sockets/manager.py
Escucha eventos de Redis y emite por WebSocket

Puede ejecutarse como microservicio Node.js o Python

app/db/models.py
Define ORM (SQLAlchemy) para guardar ejecuciones pasadas

Clave para auditoría, historial, dashboards futuros

✅ Buenas Prácticas
Módulos desacoplados (api/core/services)

Tipos compartidos entre API y lógica de negocio (types.py)

Logs emitidos por Redis permiten multiconsumo (WS + auditoría)

Testeable desde el inicio (test_execute.py ya creado)

Documentado para escalar a múltiples endpoints (/metrics, /history, /stream)