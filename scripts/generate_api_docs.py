"""Automatic API documentation generation from type hints.

Generates Markdown documentation from Python docstrings and type annotations.
"""

from __future__ import annotations

import inspect
import importlib
import sys
from pathlib import Path
from typing import Any, Callable, get_type_hints
from dataclasses import is_dataclass, fields


def generate_module_docs(module: Any) -> str:
    """Generate documentation for a Python module."""
    docs = []
    docs.append(f"# Module: {module.__name__}\n")
    
    if module.__doc__:
        docs.append(f"{module.__doc__}\n")
    
    # Document classes
    docs.append("## Classes\n")
    for name, obj in inspect.getmembers(module, inspect.isclass):
        if obj.__module__ == module.__name__:
            docs.append(_generate_class_docs(obj))
    
    # Document functions
    docs.append("## Functions\n")
    for name, obj in inspect.getmembers(module, inspect.isfunction):
        if obj.__module__ == module.__name__:
            docs.append(_generate_function_docs(obj))
    
    return "\n".join(docs)


def _generate_class_docs(cls: type) -> str:
    """Generate documentation for a class."""
    docs = []
    docs.append(f"### {cls.__name__}\n")
    
    if cls.__doc__:
        docs.append(f"{inspect.cleandoc(cls.__doc__)}\n")
    
    # Document methods
    if hasattr(cls, '__init__'):
        init_method = cls.__init__
        sig = inspect.signature(init_method)
        docs.append(f"#### Constructor\n")
        docs.append(f"```python\n{cls.__name__}{sig}\n```\n")
    
    # Document fields if dataclass
    if is_dataclass(cls):
        docs.append("#### Fields\n")
        for field in fields(cls):
            docs.append(f"- `{field.name}`: {field.type}\n")
    
    # Document methods
    docs.append("#### Methods\n")
    for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
        if not name.startswith('_'):
            sig = inspect.signature(method)
            docs.append(f"- `{name}{sig}`")
            if method.__doc__:
                docs.append(f": {inspect.cleandoc(method.__doc__)}")
            docs.append("\n")
    
    return "\n".join(docs)


def _generate_function_docs(func: Callable) -> str:
    """Generate documentation for a function."""
    docs = []
    sig = inspect.signature(func)
    docs.append(f"### {func.__name__}\n")
    docs.append(f"```python\ndef {func.__name__}{sig}:\n```\n")
    
    if func.__doc__:
        docs.append(f"{inspect.cleandoc(func.__doc__)}\n")
    
    return "\n".join(docs)


def generate_api_reference(package_path: str, output_path: str) -> None:
    """Generate API reference documentation for a package."""
    package_path_obj = Path(package_path)
    output_path_obj = Path(output_path)
    output_path_obj.parent.mkdir(parents=True, exist_ok=True)
    repo_root = package_path_obj.resolve().parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    package_root = package_path_obj.name
    
    docs = []
    docs.append("# JARVIS V8 API Reference\n")
    docs.append("Auto-generated from type hints and docstrings.\n\n")
    
    # Document all modules
    for py_file in sorted(package_path_obj.rglob("*.py")):
        if "__pycache__" in str(py_file):
            continue
        
        rel_path = py_file.relative_to(package_path_obj)
        module_parts = rel_path.with_suffix("").parts
        if module_parts[-1] == "__init__":
            module_name = ".".join((package_root, *module_parts[:-1])) if module_parts[:-1] else package_root
        else:
            module_name = ".".join((package_root, *module_parts))
        
        try:
            module = importlib.import_module(module_name)
            docs.append(generate_module_docs(module))
            docs.append("\n---\n\n")
        except Exception as e:
            print(f"Warning: Could not document {module_name}: {e}")
    
    # Write to file
    output_path_obj.write_text("\n".join(docs))
    print(f"✅ API documentation generated: {output_path}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python api_docs.py <package_path> <output_path>")
        sys.exit(1)
    
    generate_api_reference(sys.argv[1], sys.argv[2])
