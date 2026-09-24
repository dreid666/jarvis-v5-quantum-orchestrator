"""QNLP layer stub for JARVIS."""

from __future__ import annotations

from jarvis.modules.base import BaseModule


class QNLPModule(BaseModule):
    name = "qnlp"

    def initialize(self) -> None:
        self.ready = True

    def run(self, task, context=None):
        return {"module": self.name, "status": "ok", "task": getattr(task, "query", str(task))}

    def register_tools(self, registry) -> None:
        registry.register("qnlp_compile", self.run)
