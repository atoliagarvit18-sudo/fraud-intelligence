"""
app/services/__init__.py

Lazy exports for intelligence and storage services.
"""

from typing import Any

__all__ = [
    "PostClassifier",
    "ClusteringService",
    "EmbeddingService",
    "TextPreprocessor",
    "StorageService",
    "ThreatEngine",
]

_SERVICE_MAP = {
    "PostClassifier": ("app.services.classifier", "PostClassifier"),
    "ClusteringService": ("app.services.clustering", "ClusteringService"),
    "EmbeddingService": ("app.services.embeddings", "EmbeddingService"),
    "TextPreprocessor": ("app.services.preprocessing", "TextPreprocessor"),
    "StorageService": ("app.services.storage", "StorageService"),
    "ThreatEngine": ("app.services.threat_engine", "ThreatEngine"),
}


def __getattr__(name: str) -> Any:
    if name in _SERVICE_MAP:
        module_path, class_name = _SERVICE_MAP[name]
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    raise AttributeError(f"module 'app.services' has no attribute '{name}'")
