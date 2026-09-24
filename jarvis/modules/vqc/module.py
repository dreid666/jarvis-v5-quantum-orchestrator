"""VQC layer stub for JARVIS."""

from __future__ import annotations

from jarvis.modules.base import BaseModule


class VQCModule(BaseModule):
    name = "vqc"

    def initialize(self) -> None:
        self.ready = True

    def run(self, task, context=None):
        return {"module": self.name, "status": "ok", "task": getattr(task, "query", str(task))}

    def register_tools(self, registry) -> None:
        registry.register("vqc_query_project", self.run)
