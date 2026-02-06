"""
GUI Mixins Package.

Contiene mixins para dividir MainWindow en componentes más manejables.
"""

from .base_mixin import MainWindowBaseMixin
from .update_mixin import MainWindowUpdateMixin
from .transcription_mixin import MainWindowTranscriptionMixin
from .export_mixin import MainWindowExportMixin
from .ai_mixin import MainWindowAIMixin

__all__ = [
    "MainWindowBaseMixin",
    "MainWindowUpdateMixin",
    "MainWindowTranscriptionMixin",
    "MainWindowExportMixin",
    "MainWindowAIMixin",
]
