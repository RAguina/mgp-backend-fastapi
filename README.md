# 🧠 AI Agent Lab - Backend API

Este repositorio contiene la **capa API REST** que conecta el frontend del laboratorio con el entorno experimental de ejecución de modelos LLM (LangGraph, LangChain, modelos locales, etc).

---

## 🎯 Objetivo

- Recibir prompts desde el frontend (POST `/api/v1/execute`)
- Ejecutar tareas en segundo plano con el laboratorio (`AI-Agent-Lab`)
- Devolver outputs, flujos y métricas
- (Futuro) Emitir progreso a WebSocket y persistir en PostgreSQL

---

## 🛠️ Stack Tecnológico

- **FastAPI** — Framework principal (ASGI)
- **Python 3.10+**
- **Docker (opcional)** — Para entorno local completo
- **Redis (futuro)** — Para WebSocket Pub/Sub
- **PostgreSQL (futuro)** — Para historial

---

## 📁 Estructura del proyecto

backend/
├── app/
│ ├── main.py # Entrypoint FastAPI
│ ├── api/
│ │ └── v1/
│ │ ├── routes/
│ │ │ └── execute.py # POST /api/v1/execute
│ │ ├── schemas/
│ │ │ ├── execution.py # ExecutionRequest, ExecutionResult
│ │ │ └── types.py # FlowState, ExecutionMetrics, etc.
│ ├── core/
│ │ ├── config.py # Configuración desde .env
│ │ └── redis.py # Cliente Redis (futuro)
│ ├── services/
│ │ └── executor.py # Invoca el orquestador del lab
│ └── sockets/
│ └── manager.py # WebSocket listener (opcional)
├── tests/
│ └── test_execute.py # Test del endpoint
└── README.md


3. Ejecutar el servidor
venv\Scripts\Activate.ps1
uvicorn app.main:app --reload



4. Ejecutar una pregunta desde archivo con CURL
curl -X POST "http://localhost:8000/api/v1/execute" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Dime 3 números primos\", \"model\": \"mistral7b\"}"

  Invoke-RestMethod -Uri "http://localhost:8000/api/v1/execute" -Method POST -ContentType "application/json" -Body '{"prompt": "Que es Boca Juniors", "model": "mistral7b"}'


Backend → API Call → Lab Service (/orchestrate endpoint)
Backend → API Call → Lab Service (/inference endpoint)

🔄 URLs resultantes:

POST /inference/ - Simple LLM (como antes)
POST /orchestrate/ - LangGraph orchestrator (nuevo)
GET /orchestrate/ - Health check del orchestrator