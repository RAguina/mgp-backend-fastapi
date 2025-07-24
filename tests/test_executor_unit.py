# tests/test_executor_unit.py

from app.services.executor import execute_prompt
from app.api.v1.schemas.execution import ExecutionRequest
from app.api.v1.schemas.types import ExecutionResult


def test_execute_prompt_returns_result():
    request = ExecutionRequest(prompt="¿Qué es la inteligencia artificial?", model="mistral7b", strategy="optimized")
    result = execute_prompt(request)

    assert isinstance(result, ExecutionResult)
    assert isinstance(result.id, str)
    assert result.output is not None
    assert result.flow is not None
    assert result.metrics is not None
