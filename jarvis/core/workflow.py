"""Workflow graph for sequencing tasks and tool calls."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowNode:
    """A node in the execution graph."""

    name: str
    action: str
    inputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Workflow:
    """Simple DAG-style workflow container."""

    name: str
    nodes: List[WorkflowNode] = field(default_factory=list)

    def add_node(self, node: WorkflowNode) -> None:
        self.nodes.append(node)

    def get_node(self, name: str) -> Optional[WorkflowNode]:
        for node in self.nodes:
            if node.name == name:
                return node
        return None
    
    def topological_order(self) -> List[WorkflowNode]:
        """Return nodes in topological order based on dependencies."""
        visited = set()
        active = set()
        result = []
        
        def visit(node_name: str) -> None:
            if node_name in visited:
                return
            if node_name in active:
                raise ValueError(f"cycle detected at workflow node: {node_name}")
            active.add(node_name)
            
            node = self.get_node(node_name)
            if node:
                for dep in node.dependencies:
                    visit(dep)
                visited.add(node_name)
                result.append(node)
            active.remove(node_name)
        
        for node in self.nodes:
            visit(node.name)
        
        return result
