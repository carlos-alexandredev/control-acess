"""
Pacote raiz para a integração Control iD.

Importa conveniências de nível superior do cliente.
"""

from .client import ControlIDClient, ControlIDError  # noqa: F401

__all__ = ["ControlIDClient", "ControlIDError"]