"""
Tests para el sistema de verificación de integridad.

Estos tests verifican:
- Cálculo de hashes SHA-256
- Generación de manifests de integridad
- Verificación de integridad de archivos
- Manejo de archivos faltantes o modificados
- Funciones helper de verificación
"""

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Añadir el directorio raíz del proyecto al PATH
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from src.core.integrity_checker import (
    IntegrityChecker,
    IntegrityReport,
    IntegrityResult,
    integrity_checker,
    verify_critical_files_exist,
)


class TestIntegrityChecker(unittest.TestCase):
    """Tests para el verificador de integridad."""

    def setUp(self):
        """Configuración antes de cada test."""
        # Crear directorio temporal
        self.temp_dir = tempfile.mkdtemp()

        # Crear archivos de prueba
        self.test_file = Path(self.temp_dir) / "test_file.py"
        self.test_file.write_text("print('test')")

        self.test_content = b"test content for hashing"
        self.test_file_binary = Path(self.temp_dir) / "test_binary.bin"
        self.test_file_binary.write_bytes(self.test_content)

        # Instancia del checker
        self.checker = IntegrityChecker(project_root=self.temp_dir)

    def tearDown(self):
        """Limpieza después de cada test."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_calculate_file_hash_text(self):
        """Verifica cálculo de hash para archivo de texto."""
        file_hash = self.checker.calculate_file_hash(self.test_file)

        # Calcular hash esperado
        expected_hash = hashlib.sha256(self.test_file.read_bytes()).hexdigest()

        self.assertIsNotNone(file_hash)
        self.assertEqual(file_hash, expected_hash)
        self.assertEqual(len(file_hash), 64)  # SHA-256 produce 64 caracteres hex

    def test_calculate_file_hash_binary(self):
        """Verifica cálculo de hash para archivo binario."""
        file_hash = self.checker.calculate_file_hash(self.test_file_binary)

        expected_hash = hashlib.sha256(self.test_content).hexdigest()

        self.assertIsNotNone(file_hash)
        self.assertEqual(file_hash, expected_hash)

    def test_calculate_file_hash_nonexistent(self):
        """Verifica manejo de archivo inexistente."""
        nonexistent = Path(self.temp_dir) / "nonexistent.py"
        file_hash = self.checker.calculate_file_hash(nonexistent)

        self.assertIsNone(file_hash)

    def test_generate_manifest(self):
        """Verifica generación de manifest de integridad."""
        # Crear archivo Python de prueba
        py_file = Path(self.temp_dir) / "src" / "core" / "test_module.py"
        py_file.parent.mkdir(parents=True)
        py_file.write_text("def test(): pass")

        # Crear manifest
        manifest = self.checker.generate_manifest()

        # Verificar que se generó
        self.assertIsNotNone(manifest)
        self.assertIsInstance(manifest, dict)
        self.assertGreater(len(manifest), 0)

        # Verificar que existe el archivo de manifest
        manifest_path = Path(self.temp_dir) / "integrity_manifest.json"
        self.assertTrue(manifest_path.exists())

    def test_generate_manifest_with_patterns(self):
        """Verifica generación con patrones personalizados."""
        # Crear archivos de prueba
        (Path(self.temp_dir) / "file1.py").write_text("print(1)")
        (Path(self.temp_dir) / "file2.py").write_text("print(2)")

        patterns = ["*.py"]
        manifest = self.checker.generate_manifest(include_patterns=patterns)

        self.assertIsNotNone(manifest)
        # Debe incluir al menos los archivos que coinciden
        self.assertGreaterEqual(len(manifest), 2)

    def test_load_manifest_success(self):
        """Verifica carga exitosa de manifest."""
        # Crear manifest de prueba
        manifest_data = {
            "version": "1.0",
            "files": {"src/main.py": "abc123", "src/core/module.py": "def456"},
        }

        manifest_path = Path(self.temp_dir) / "integrity_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        # Cargar
        loaded = self.checker.load_manifest()

        self.assertIsNotNone(loaded)
        self.assertEqual(loaded["src/main.py"], "abc123")
        self.assertEqual(loaded["src/core/module.py"], "def456")

    def test_load_manifest_simple_format(self):
        """Verifica carga de manifest en formato simple (solo archivos)."""
        # Crear manifest sin metadata
        manifest_data = {"src/main.py": "abc123", "src/core/module.py": "def456"}

        manifest_path = Path(self.temp_dir) / "integrity_manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest_data, f)

        loaded = self.checker.load_manifest()

        self.assertIsNotNone(loaded)
        self.assertEqual(len(loaded), 2)

    def test_load_manifest_nonexistent(self):
        """Verifica manejo de manifest inexistente."""
        loaded = self.checker.load_manifest()
        self.assertIsNone(loaded)

    def test_load_manifest_invalid_json(self):
        """Verifica manejo de JSON inválido."""
        manifest_path = Path(self.temp_dir) / "integrity_manifest.json"
        manifest_path.write_text("invalid json {{{")

        loaded = self.checker.load_manifest()
        self.assertIsNone(loaded)

    def test_verify_integrity_all_valid(self):
        """Verifica verificación cuando todos los archivos son válidos."""
        # Crear archivo de prueba
        test_file = Path(self.temp_dir) / "src" / "main.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("print('hello')")

        # Calcular hash
        file_hash = self.checker.calculate_file_hash(test_file)

        # Crear manifest
        manifest = {"src/main.py": file_hash}

        # Verificar
        report = self.checker.verify_integrity(manifest)

        self.assertIsInstance(report, IntegrityReport)
        self.assertTrue(report.is_valid)
        self.assertEqual(report.total_files, 1)
        self.assertEqual(report.valid_files, 1)
        self.assertEqual(report.invalid_files, 0)
        self.assertEqual(report.missing_files, 0)

    def test_verify_integrity_modified_file(self):
        """Verifica detección de archivo modificado."""
        # Crear archivo
        test_file = Path(self.temp_dir) / "src" / "main.py"
        test_file.parent.mkdir(parents=True)
        test_file.write_text("original content")

        # Crear manifest con hash diferente
        manifest = {
            "src/main.py": "0000000000000000000000000000000000000000000000000000000000000000"
        }

        # Verificar
        report = self.checker.verify_integrity(manifest)

        self.assertFalse(report.is_valid)
        self.assertEqual(report.invalid_files, 1)
        self.assertEqual(report.valid_files, 0)

    def test_verify_integrity_missing_file(self):
        """Verifica detección de archivo faltante."""
        # Manifest con archivo que no existe
        manifest = {"src/nonexistent.py": "abc123"}

        # Verificar
        report = self.checker.verify_integrity(manifest)

        self.assertFalse(report.is_valid)
        self.assertEqual(report.missing_files, 1)
        self.assertEqual(report.total_files, 1)

    def test_verify_integrity_without_manifest(self):
        """Verifica comportamiento cuando no hay manifest."""
        # Crear algunos archivos críticos
        (Path(self.temp_dir) / "src" / "core").mkdir(parents=True)
        (Path(self.temp_dir) / "src" / "core" / "transcriber_engine.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "core" / "validators.py").write_text("pass")

        report = self.checker.verify_integrity(manifest=None, critical_only=True)

        # Debe verificar archivos críticos básicos
        self.assertIsInstance(report, IntegrityReport)
        # Sin manifest, solo verifica existencia, no hash

    def test_quick_check_all_exist(self):
        """Verifica quick_check cuando todos los archivos existen."""
        # Crear los 5 archivos críticos que verifica quick_check (primeros 5 de CRITICAL_FILES)
        (Path(self.temp_dir) / "src" / "core").mkdir(parents=True)
        (Path(self.temp_dir) / "src" / "gui").mkdir(parents=True)

        # Crear los 5 archivos que quick_check verifica sin manifest
        (Path(self.temp_dir) / "src" / "core" / "transcriber_engine.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "core" / "audio_handler.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "core" / "validators.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "core" / "logger.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "main.py").write_text("pass")

        result = self.checker.quick_check()
        self.assertTrue(result)

    def test_quick_check_missing_file(self):
        """Verifica quick_check cuando falta un archivo."""
        # No crear ningún archivo
        result = self.checker.quick_check()
        self.assertFalse(result)

    def test_integrity_report_to_dict(self):
        """Verifica conversión de reporte a diccionario."""
        result = IntegrityResult(
            file_path="test.py",
            expected_hash="abc123",
            actual_hash="abc123",
            is_valid=True,
        )

        report = IntegrityReport(
            timestamp="2024-01-01T00:00:00",
            total_files=1,
            valid_files=1,
            invalid_files=0,
            missing_files=0,
            results=[result],
            is_valid=True,
        )

        report_dict = report.to_dict()

        self.assertEqual(report_dict["total_files"], 1)
        self.assertEqual(report_dict["valid_files"], 1)
        self.assertTrue(report_dict["is_valid"])
        self.assertEqual(len(report_dict["results"]), 1)

    def test_integrity_report_to_json(self):
        """Verifica conversión de reporte a JSON."""
        report = IntegrityReport(
            timestamp="2024-01-01T00:00:00",
            total_files=0,
            valid_files=0,
            invalid_files=0,
            missing_files=0,
            results=[],
            is_valid=True,
        )

        json_str = report.to_json()

        self.assertIsInstance(json_str, str)
        # Verificar que es JSON válido
        parsed = json.loads(json_str)
        self.assertEqual(parsed["total_files"], 0)

    def test_generate_installer_hash_success(self):
        """Verifica generación de hash de instalador exitosa."""
        # Crear archivo de instalador simulado
        installer = Path(self.temp_dir) / "installer.exe"
        installer.write_bytes(b"fake installer content")

        hash_result = self.checker.generate_installer_hash(str(installer))

        self.assertIsNotNone(hash_result)
        self.assertEqual(len(hash_result), 64)

        # Verificar que se creó el archivo .sha256
        hash_file = Path(self.temp_dir) / "installer.exe.sha256"
        self.assertTrue(hash_file.exists())

    def test_generate_installer_hash_nonexistent(self):
        """Verifica manejo de instalador inexistente."""
        nonexistent = Path(self.temp_dir) / "nonexistent.exe"

        hash_result = self.checker.generate_installer_hash(str(nonexistent))

        self.assertIsNone(hash_result)


class TestVerifyCriticalFilesExist(unittest.TestCase):
    """Tests para la función helper verify_critical_files_exist."""

    def setUp(self):
        """Configuración antes de cada test."""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Limpieza después de cada test."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_all_files_exist(self):
        """Verifica cuando todos los archivos críticos existen."""
        # Crear estructura mínima
        (Path(self.temp_dir) / "src" / "core").mkdir(parents=True)
        (Path(self.temp_dir) / "src" / "core" / "transcriber_engine.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "core" / "audio_handler.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "core" / "validators.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "core" / "logger.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "gui").mkdir(parents=True)
        (Path(self.temp_dir) / "src" / "gui" / "main_window.py").write_text("pass")
        (Path(self.temp_dir) / "src" / "main.py").write_text("pass")

        all_exist, missing = verify_critical_files_exist(self.temp_dir)

        self.assertTrue(all_exist)
        self.assertEqual(len(missing), 0)

    def test_some_files_missing(self):
        """Verifica cuando faltan algunos archivos."""
        # Crear solo algunos archivos
        (Path(self.temp_dir) / "src" / "core").mkdir(parents=True)
        (Path(self.temp_dir) / "src" / "core" / "transcriber_engine.py").write_text("pass")
        # Faltan otros archivos...

        all_exist, missing = verify_critical_files_exist(self.temp_dir)

        self.assertFalse(all_exist)
        self.assertGreater(len(missing), 0)

    def test_no_files_exist(self):
        """Verifica cuando no existe ningún archivo."""
        all_exist, missing = verify_critical_files_exist(self.temp_dir)

        self.assertFalse(all_exist)
        self.assertGreater(len(missing), 0)


class TestIntegrityCheckerSingleton(unittest.TestCase):
    """Tests para la instancia global del integrity checker."""

    def test_singleton_instance(self):
        """Verifica que la instancia global existe."""
        from src.core.integrity_checker import integrity_checker

        self.assertIsInstance(integrity_checker, IntegrityChecker)
        self.assertIsNotNone(integrity_checker.project_root)


class TestIntegrityResult(unittest.TestCase):
    """Tests para la clase IntegrityResult."""

    def test_result_creation_valid(self):
        """Verifica creación de resultado válido."""
        result = IntegrityResult(
            file_path="src/main.py",
            expected_hash="abc123",
            actual_hash="abc123",
            is_valid=True,
        )

        self.assertEqual(result.file_path, "src/main.py")
        self.assertEqual(result.file_name, "main.py")
        self.assertTrue(result.is_valid)
        self.assertIsNone(result.error_message)

    def test_result_creation_invalid(self):
        """Verifica creación de resultado inválido."""
        result = IntegrityResult(
            file_path="src/main.py",
            expected_hash="abc123",
            actual_hash="xyz789",
            is_valid=False,
            error_message="Hash no coincide",
        )

        self.assertFalse(result.is_valid)
        self.assertEqual(result.error_message, "Hash no coincide")

    def test_result_file_name_property(self):
        """Verifica propiedad file_name."""
        result = IntegrityResult(
            file_path="/home/user/project/src/main.py",
            expected_hash="abc",
            actual_hash="abc",
            is_valid=True,
        )

        self.assertEqual(result.file_name, "main.py")


if __name__ == "__main__":
    unittest.main()
