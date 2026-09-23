# JARVIS v7 — Quantum-Classical AI Orchestrator

A fully integrated, NISQ-friendly quantum-classical AI orchestration system.

## Modules

| File | Purpose |
|---|---|
| `jarvis_v7.py` | Core orchestrator entrypoint for the v7 runtime |
| `jarvis_vqc_layer.py` | PennyLane VQC Query projection (parameter-shift gradients) |
| `jarvis_aletheia.py` | Aletheia fact-checker — claim decomposition + 3D EQ scoring |
| `jarvis_qnlp.py` | QNLP compiler — CCG to string diagrams to IQP/MPS circuits to QASM |
| `jarvis_v7_integrated.py` | All modules wired into one unified DAG |
| `jarvis_launch.py` | One-command launcher with CLI + interactive REPL |

## Quick Start

```bash
pip install -r requirements_unified.txt
export TAVILY_API_KEY=your_key_here
python jarvis_launch.py --interactive
```

## CLI Options

```bash
python jarvis_launch.py --query "Your query" --domain quantum_architect
python jarvis_launch.py --status
python jarvis_launch.py --interactive
```
