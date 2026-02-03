"""
Sistema de verificación de integridad para DesktopWhisperTranscriber.

Este módulo proporciona funcionalidad para verificar la integridad de los archivos
de la aplicación mediante hashes SHA-256, detectando posibles modificaciones
no autorizadas o corrupción de archivos.

Características:
- Verificación de archivos críticos al inicio de la aplicación
- Comparación de hashes SHA-256
- Generación de manifests de integridad
- Alertas ante modificaciones detectadas
"""

import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
from dataclasses import dataclass, asdict
from datetime import datetime

from src.core.logger import logger
from src.core.exceptions import SecurityError


@dataclass
class IntegrityResult:
    """Resultado de una verificación de integridad."""

    file_path: str
    expected_hash: Optional[str]
    actual_hash: Optional[str]
    is_valid: bool
    error_message: Optional[str] = None

    @property
    def file_name(self) -> str:
        """Obtiene solo el nombre del archivo."""
        return Path(self.file_path).name


@dataclass
class IntegrityReport:
    """Reporte completo de verificación de integridad."""

    timestamp: str
    total_files: int
    valid_files: int
    invalid_files: int
    missing_files: int
    results: List[IntegrityResult]
    is_valid: bool

    def to_dict(self) -> Dict:
        """Convierte el reporte a diccionario."""
        return {
            "timestamp": self.timestamp,
            "total_files": self.total_files,
            "valid_files": self.valid_files,
            "invalid_files": self.invalid_files,
            "missing_files": self.missing_files,
            "is_valid": self.is_valid,
            "results": [
                {
                    "file_path": r.file_path,
                    "file_name": r.file_name,
                    "expected_hash": r.expected_hash,
                    "actual_hash": r.actual_hash,
                    "is_valid": r.is_valid,
                    "error_message": r.error_message,
                }
                for r in self.results
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convierte el reporte a JSON."""
        return json.dumps(self.to_dict(), indent=indent)


class IntegrityChecker:
    """
    Verificador de integridad de archivos de la aplicación.

    Compara los hashes SHA-256 de los archivos críticos con los hashes
    esperados almacenados en un manifest, detectando cualquier modificación.

    Attributes:
        MANIFEST_FILENAME: Nombre del archivo de manifest
        CRITICAL_EXTENSIONS: Extensiones de archivos a verificar
        manifest_path: Ruta al archivo de manifest
        project_root: Directorio raíz del proyecto
    """

    MANIFEST_FILENAME = "integrity_manifest.json"

    # Archivos críticos que deben verificarse
    CRITICAL_PATTERNS = [
        "src/core/*.py",
        "src/gui/*.py",
        "src/gui/components/*.py",
        "src/gui/theme/*.py",
        "src/gui/utils/*.py",
    ]

    # Archivos específicos que siempre deben verificarse
    CRITICAL_FILES = [
        "src/main.py",
        "src/core/transcriber_engine.py",
        "src/core/audio_handler.py",
        "src/core/validators.py",
        "src/core/logger.py",
        "src/core/exceptions.py",
        "src/gui/main_window.py",
    ]

    def __init__(
        self,
        project_root: Optional[str] = None,
        manifest_path: Optional[str] = None,
        on_integrity_failure: Optional[Callable[[IntegrityReport], None]] = None,
    ):
        """
        Inicializa el verificador de integridad.

        Args:
            project_root: Directorio raíz del proyecto (auto-detectado si None)
            manifest_path: Ruta al archivo de manifest (auto-detectada si None)
            on_integrity_failure: Callback cuando falla la verificación
        """
        if project_root:
            self.project_root = Path(project_root)
        else:
            # Auto-detectar desde la ubicación de este archivo
            self.project_root = Path(__file__).parent.parent.parent

        if manifest_path:
            self.manifest_path = Path(manifest_path)
        else:
            self.manifest_path = self.project_root / self.MANIFEST_FILENAME

        self.on_integrity_failure = on_integrity_failure

        logger.info(f"IntegrityChecker inicializado. Root: {self.project_root}")

    def calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """
        Calcula el hash SHA-256 de un archivo.

        Args:
            file_path: Ruta al archivo

        Returns:
            Optional[str]: Hash SHA-256 en hexadecimal o None si falla
        """
        try:
            sha256_hash = hashlib.sha256()

            # Leer archivo en chunks para archivos grandes
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    sha256_hash.update(chunk)

            return sha256_hash.hexdigest()
        except (IOError, OSError) as e:
            logger.error(f"Error calculando hash de {file_path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error inesperado calculando hash de {file_path}: {e}")
            return None

    def generate_manifest(
        self,
        output_path: Optional[str] = None,
        include_patterns: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        Genera un manifest de integridad con los hashes de los archivos críticos.

        Este método debe ejecutarse durante el proceso de build/release para
        generar el manifest de referencia.

        Args:
            output_path: Ruta donde guardar el manifest (usa self.manifest_path si None)
            include_patterns: Patrones adicionales de archivos a incluir

        Returns:
            Dict[str, str]: Diccionario de {ruta_relativa: hash}
        """
        import glob

        manifest = {}

        # Archivos específicos críticos
        for file_path in self.CRITICAL_FILES:
            full_path = self.project_root / file_path
            if full_path.exists():
                file_hash = self.calculate_file_hash(full_path)
                if file_hash:
                    manifest[file_path] = file_hash
                    logger.debug(f"Hash generado: {file_path} = {file_hash[:16]}...")

        # Archivos por patrón
        patterns = include_patterns or self.CRITICAL_PATTERNS
        for pattern in patterns:
            search_path = str(self.project_root / pattern)
            for file_path in glob.glob(search_path, recursive=True):
                path_obj = Path(file_path)
                if path_obj.is_file():
                    relative_path = str(
                        path_obj.relative_to(self.project_root)
                    ).replace("\\", "/")

                    # Evitar duplicados
                    if relative_path not in manifest:
                        file_hash = self.calculate_file_hash(path_obj)
                        if file_hash:
                            manifest[relative_path] = file_hash
                            logger.debug(
                                f"Hash generado: {relative_path} = {file_hash[:16]}..."
                            )

        # Guardar manifest
        output_file = Path(output_path) if output_path else self.manifest_path
        try:
            manifest_data = {
                "version": "1.0",
                "generated_at": datetime.now().isoformat(),
                "total_files": len(manifest),
                "files": manifest,
            }

            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(manifest_data, f, indent=2)

            logger.info(
                f"Manifest de integridad generado: {output_file} ({len(manifest)} archivos)"
            )

        except Exception as e:
            logger.error(f"Error guardando manifest: {e}")

        return manifest

    def load_manifest(self) -> Optional[Dict[str, str]]:
        """
        Carga el manifest de integridad desde el archivo.

        Returns:
            Optional[Dict[str, str]]: Diccionario de {ruta_relativa: hash} o None
        """
        try:
            if not self.manifest_path.exists():
                logger.warning(
                    f"Manifest de integridad no encontrado: {self.manifest_path}"
                )
                return None

            with open(self.manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)

            # Soportar ambos formatos: con metadata o solo archivos
            if "files" in manifest_data:
                files = manifest_data["files"]
            else:
                files = manifest_data

            logger.info(f"Manifest cargado: {len(files)} archivos")
            return files

        except json.JSONDecodeError as e:
            logger.error(f"Error parseando manifest JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error cargando manifest: {e}")
            return None

    def verify_integrity(
        self, manifest: Optional[Dict[str, str]] = None, critical_only: bool = True
    ) -> IntegrityReport:
        """
        Verifica la integridad de los archivos comparándolos con el manifest.

        Args:
            manifest: Diccionario de hashes esperados (carga desde archivo si None)
            critical_only: Si True, solo verifica archivos críticos si no hay manifest

        Returns:
            IntegrityReport: Reporte de verificación
        """
        if manifest is None:
            manifest = self.load_manifest()

        results = []
        total_files = 0
        valid_files = 0
        invalid_files = 0
        missing_files = 0

        if manifest:
            # Verificar todos los archivos en el manifest
            files_to_check = manifest.keys()
        else:
            # Sin manifest: verificar solo archivos críticos básicos
            if critical_only:
                files_to_check = self.CRITICAL_FILES
                logger.warning(
                    "No hay manifest de integridad. Verificando solo archivos críticos básicos."
                )
            else:
                logger.error(
                    "No hay manifest de integridad. No se puede verificar integridad."
                )
                return IntegrityReport(
                    timestamp=datetime.now().isoformat(),
                    total_files=0,
                    valid_files=0,
                    invalid_files=0,
                    missing_files=0,
                    results=[],
                    is_valid=False,
                )

        for file_path in files_to_check:
            total_files += 1
            full_path = self.project_root / file_path

            # Verificar si existe
            if not full_path.exists():
                missing_files += 1
                result = IntegrityResult(
                    file_path=file_path,
                    expected_hash=manifest.get(file_path) if manifest else None,
                    actual_hash=None,
                    is_valid=False,
                    error_message="Archivo no encontrado",
                )
                results.append(result)
                logger.security(f"[INTEGRITY] Archivo crítico faltante: {file_path}")
                continue

            # Calcular hash actual
            actual_hash = self.calculate_file_hash(full_path)

            if actual_hash is None:
                invalid_files += 1
                result = IntegrityResult(
                    file_path=file_path,
                    expected_hash=manifest.get(file_path) if manifest else None,
                    actual_hash=None,
                    is_valid=False,
                    error_message="Error calculando hash",
                )
                results.append(result)
                continue

            # Si hay manifest, comparar hashes
            if manifest and file_path in manifest:
                expected_hash = manifest[file_path]

                if actual_hash == expected_hash:
                    valid_files += 1
                    result = IntegrityResult(
                        file_path=file_path,
                        expected_hash=expected_hash,
                        actual_hash=actual_hash,
                        is_valid=True,
                    )
                    logger.debug(f"[INTEGRITY] OK: {file_path}")
                else:
                    invalid_files += 1
                    result = IntegrityResult(
                        file_path=file_path,
                        expected_hash=expected_hash,
                        actual_hash=actual_hash,
                        is_valid=False,
                        error_message="Hash no coincide - archivo modificado",
                    )
                    logger.security(f"[INTEGRITY] MODIFICADO: {file_path}")
                    logger.security(f"  Esperado: {expected_hash[:16]}...")
                    logger.security(f"  Actual:   {actual_hash[:16]}...")
            else:
                # Sin hash esperado, solo verificamos que exista
                valid_files += 1
                result = IntegrityResult(
                    file_path=file_path,
                    expected_hash=None,
                    actual_hash=actual_hash,
                    is_valid=True,
                )

        # Determinar si todo es válido
        is_valid = invalid_files == 0 and missing_files == 0

        report = IntegrityReport(
            timestamp=datetime.now().isoformat(),
            total_files=total_files,
            valid_files=valid_files,
            invalid_files=invalid_files,
            missing_files=missing_files,
            results=results,
            is_valid=is_valid,
        )

        if is_valid:
            logger.info(
                f"[INTEGRITY] Verificación exitosa: {valid_files}/{total_files} archivos válidos"
            )
        else:
            logger.warning(
                f"[INTEGRITY] Verificación fallida: {invalid_files} inválidos, {missing_files} faltantes"
            )
            if self.on_integrity_failure:
                self.on_integrity_failure(report)

        return report

    def quick_check(self) -> bool:
        """
        Verificación rápida de integridad (solo archivos más críticos).

        Returns:
            bool: True si todos los archivos críticos son válidos
        """
        manifest = self.load_manifest()

        if not manifest:
            # Sin manifest, solo verificar existencia de archivos críticos
            all_exist = True
            for file_path in self.CRITICAL_FILES[:5]:  # Solo los 5 más críticos
                full_path = self.project_root / file_path
                if not full_path.exists():
                    logger.security(
                        f"[INTEGRITY] Archivo crítico faltante: {file_path}"
                    )
                    all_exist = False

            return all_exist

        # Con manifest, verificar solo algunos archivos críticos
        critical_in_manifest = [f for f in self.CRITICAL_FILES if f in manifest]
        sample = critical_in_manifest[:5]  # Máximo 5 para ser rápido

        for file_path in sample:
            full_path = self.project_root / file_path
            if not full_path.exists():
                logger.security(f"[INTEGRITY] Archivo crítico faltante: {file_path}")
                return False

            actual_hash = self.calculate_file_hash(full_path)
            if actual_hash != manifest[file_path]:
                logger.security(f"[INTEGRITY] Archivo modificado: {file_path}")
                return False

        return True

    def generate_installer_hash(self, installer_path: str) -> Optional[str]:
        """
        Genera el hash SHA-256 de un instalador/executable.

        Este método se usa durante el build para generar el hash del instalador.

        Args:
            installer_path: Ruta al instalador/executable

        Returns:
            Optional[str]: Hash SHA-256 o None si falla
        """
        try:
            installer = Path(installer_path)
            if not installer.exists():
                logger.error(f"Instalador no encontrado: {installer_path}")
                return None

            file_hash = self.calculate_file_hash(installer)

            if file_hash:
                logger.info(f"Hash del instalador generado: {file_hash}")

                # Guardar hash en archivo adjunto
                hash_file = installer.parent / f"{installer.name}.sha256"
                try:
                    with open(hash_file, "w") as f:
                        f.write(f"{file_hash}  {installer.name}\n")
                    logger.info(f"Hash guardado en: {hash_file}")
                except Exception as e:
                    logger.warning(f"No se pudo guardar archivo de hash: {e}")

            return file_hash

        except Exception as e:
            logger.error(f"Error generando hash del instalador: {e}")
            return None


def verify_critical_files_exist(
    project_root: Optional[str] = None,
) -> Tuple[bool, List[str]]:
    """
    Función helper para verificar rápidamente que existan los archivos críticos.

    Args:
        project_root: Directorio raíz (auto-detectado si None)

    Returns:
        Tuple[bool, List[str]]: (todos_existen, lista_de_faltantes)
    """
    if project_root:
        root = Path(project_root)
    else:
        root = Path(__file__).parent.parent.parent

    critical_files = [
        "src/core/transcriber_engine.py",
        "src/core/audio_handler.py",
        "src/core/validators.py",
        "src/core/logger.py",
        "src/gui/main_window.py",
        "src/main.py",
    ]

    missing = []
    for file_path in critical_files:
        full_path = root / file_path
        if not full_path.exists():
            missing.append(file_path)

    all_exist = len(missing) == 0

    if not all_exist:
        logger.security(f"[INTEGRITY] Archivos críticos faltantes: {missing}")

    return all_exist, missing


# Instancia global para uso conveniente
integrity_checker = IntegrityChecker()
