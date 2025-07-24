# backend/app/api/v1/schemas/types.py

from typing import List, Optional, Literal
from pydantic import BaseModel


class NodeState(BaseModel):
    id: str
    name: str
    type: str
    status: Literal['pending', 'running', 'completed', 'error']
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    output: Optional[str] = None
    error: Optional[str] = None


class Edge(BaseModel):
    source: str
    target: str
    label: Optional[str] = None


class FlowState(BaseModel):
    nodes: List[NodeState]
    edges: List[Edge]
    current_node: Optional[str] = None


class ExecutionMetrics(BaseModel):
    total_time: float
    tokens_generated: Optional[int] = None
    models_used: Optional[List[str]] = None
