"""
Script de build mejorado para DesktopWhisperTranscriber.

Este script:
1. Genera el manifest de integridad (integrity_manifest.json)
2. Compila la aplicación con PyInstaller
3. Genera el hash SHA-256 del instalador/executable
4. Crea un archivo de metadatos del release

Uso:
    python build.py [opciones]

Opciones:
    --no-integrity    : Omitir generación de manifest de integridad
    --onefile         : Crear un solo archivo ejecutable
    --windowed        : Modo ventana (sin consola)

Ejemplo:
    python build.py --onefile --windowed
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime

# Asegurar que podemos importar desde el proyecto
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

from src.core.integrity_checker import IntegrityChecker


def calculate_sha256(file_path: Path) -> str:
    """Calcula el hash SHA-256 de un archivo."""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


def generate_integrity_manifest(project_root: Path) -> Path:
    """Genera el manifest de integridad de los archivos fuente."""
    print("🔐 Generando manifest de integridad...")

    checker = IntegrityChecker(project_root=str(project_root))
    manifest = checker.generate_manifest()

    manifest_path = project_root / "integrity_manifest.json"

    if manifest_path.exists():
        print(f"✅ Manifest generado: {manifest_path}")
        print(f"   Total archivos: {len(manifest)}")
        return manifest_path
    else:
        print(f"❌ Error: No se pudo generar el manifest")
        return None


def build_with_pyinstaller(
    project_root: Path, onefile: bool = True, windowed: bool = True
) -> Path:
    """Compila la aplicación con PyInstaller."""
    print("🔨 Compilando con PyInstaller...")

    spec_file = project_root / "DesktopWhisperTranscriber.spec"

    if not spec_file.exists():
        # Intentar con main.spec
        spec_file = project_root / "main.spec"

    if not spec_file.exists():
        print(f"❌ Error: No se encontró archivo .spec")
        return None

    # Limpiar builds anteriores
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    if dist_dir.exists():
        print("🧹 Limpiando builds anteriores...")
        import shutil

        shutil.rmtree(dist_dir, ignore_errors=True)

    # Ejecutar PyInstaller
    cmd = [sys.executable, "-m", "PyInstaller", str(spec_file), "--clean"]

    if onefile:
        cmd.append("--onefile")
    if windowed:
        cmd.append("--windowed")

    print(f"   Comando: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd, cwd=project_root, capture_output=True, text=True, check=True
        )
        print("✅ PyInstaller completado exitosamente")

        # Buscar el ejecutable generado
        if onefile:
            exe_path = dist_dir / "DesktopWhisperTranscriber.exe"
            if not exe_path.exists():
                exe_path = dist_dir / "main.exe"
        else:
            exe_path = (
                dist_dir / "DesktopWhisperTranscriber" / "DesktopWhisperTranscriber.exe"
            )

        if exe_path.exists():
            print(f"✅ Ejecutable generado: {exe_path}")
            return exe_path
        else:
            print(f"⚠️ No se encontró el ejecutable en la ruta esperada")
            # Listar archivos en dist
            if dist_dir.exists():
                print("   Archivos en dist/:")
                for item in dist_dir.iterdir():
                    print(f"     - {item.name}")
            return None

    except subprocess.CalledProcessError as e:
        print(f"❌ Error en PyInstaller:")
        print(f"   stdout: {e.stdout}")
        print(f"   stderr: {e.stderr}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None


def generate_installer_hash(exe_path: Path) -> tuple:
    """Genera el hash SHA-256 del instalador/executable."""
    print("🔑 Generando hash del instalador...")

    try:
        file_hash = calculate_sha256(exe_path)

        # Guardar hash en archivo
        hash_file = exe_path.parent / f"{exe_path.name}.sha256"
        with open(hash_file, "w") as f:
            f.write(f"{file_hash}  {exe_path.name}\n")

        print(f"✅ Hash generado: {file_hash}")
        print(f"✅ Hash guardado en: {hash_file}")

        return file_hash, hash_file

    except Exception as e:
        print(f"❌ Error generando hash: {e}")
        return None, None


def create_release_metadata(
    project_root: Path, exe_path: Path, file_hash: str, version: str
) -> Path:
    """Crea el archivo de metadatos del release."""
    print("📝 Creando metadatos del release...")

    metadata = {
        "version": version,
        "build_date": datetime.now().isoformat(),
        "executable": {
            "filename": exe_path.name,
            "path": str(exe_path.relative_to(project_root)),
            "sha256": file_hash,
            "size_bytes": exe_path.stat().st_size,
        },
        "integrity_manifest": "integrity_manifest.json",
        "build_info": {
            "python_version": sys.version,
            "platform": sys.platform,
            "build_tool": "PyInstaller",
        },
        "verification": {
            "windows_cmd": f"certutil -hashfile {exe_path.name} SHA256",
            "powershell": f"Get-FileHash {exe_path.name} -Algorithm SHA256",
            "unix": f"sha256sum {exe_path.name}",
        },
    }

    metadata_path = project_root / "dist" / "release_metadata.json"

    try:
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        print(f"✅ Metadatos guardados en: {metadata_path}")
        return metadata_path

    except Exception as e:
        print(f"❌ Error creando metadatos: {e}")
        return None


def create_verification_guide(project_root: Path) -> Path:
    """Crea una guía de verificación para usuarios."""
    print("📖 Creando guía de verificación...")

    guide_content = """# 🔐 Verificación de Integridad

Esta guía te ayuda a verificar que el ejecutable de DesktopWhisperTranscriber no ha sido modificado.

## Windows

### Opción 1: PowerShell (Recomendado)
```powershell
Get-FileHash DesktopWhisperTranscriber.exe -Algorithm SHA256
```

### Opción 2: Command Prompt
```cmd
certutil -hashfile DesktopWhisperTranscriber.exe SHA256
```

### Opción 3: Usando el archivo .sha256
1. Abre el archivo `DesktopWhisperTranscriber.exe.sha256`
2. Compara el hash con el generado por los comandos anteriores

## macOS / Linux

```bash
sha256sum DesktopWhisperTranscriber.exe
```

## Verificación Exitosa ✅

Si el hash que obtienes coincide con el publicado en el release de GitHub, el archivo es auténtico.

Si el hash NO coincide ⚠️:
- No ejecutes el archivo
- Descárgalo nuevamente desde GitHub
- Verifica tu conexión a internet
- Reporta el incidente en: https://github.com/JoseDiazCodes/DesktopWhisperTranscriber/issues

## ¿Por qué es importante?

La verificación de integridad te protege contra:
- Archivos corruptos por errores de descarga
- Modificaciones maliciosas por terceros
- Versiones falsificadas de la aplicación

Mantén tu sistema seguro verificando siempre los ejecutables antes de instalar.
"""

    guide_path = project_root / "dist" / "VERIFICATION.md"

    try:
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide_content)

        print(f"✅ Guía creada en: {guide_path}")
        return guide_path

    except Exception as e:
        print(f"❌ Error creando guía: {e}")
        return None


def copy_version_file(project_root: Path, dist_dir: Path):
    """Copia el archivo VERSION a la carpeta de distribución."""
    version_file = project_root / "VERSION"

    if version_file.exists():
        import shutil

        dest = dist_dir / "VERSION"
        shutil.copy(version_file, dest)
        print(f"✅ Archivo VERSION copiado a {dest}")
        return True
    else:
        print(f"⚠️ Archivo VERSION no encontrado")
        return False


def main():
    """Función principal del script de build."""
    parser = argparse.ArgumentParser(
        description="Build script para DesktopWhisperTranscriber con verificación de integridad"
    )
    parser.add_argument(
        "--no-integrity",
        action="store_true",
        help="Omitir generación de manifest de integridad",
    )
    parser.add_argument(
        "--onefile",
        action="store_true",
        default=True,
        help="Crear un solo archivo ejecutable (default: True)",
    )
    parser.add_argument(
        "--windowed",
        action="store_true",
        default=True,
        help="Modo ventana sin consola (default: True)",
    )
    parser.add_argument(
        "--version", default="1.0.0", help="Versión del release (default: 1.0.0)"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("🔨 DesktopWhisperTranscriber - Build Script")
    print("=" * 60)
    print()

    project_root = Path(__file__).parent.absolute()

    # Paso 1: Generar manifest de integridad
    manifest_path = None
    if not args.no_integrity:
        manifest_path = generate_integrity_manifest(project_root)
        if not manifest_path:
            print("⚠️ Continuando sin manifest de integridad...")
    else:
        print("⏭️ Omitiendo generación de manifest de integridad")

    print()

    # Paso 2: Compilar con PyInstaller
    exe_path = build_with_pyinstaller(
        project_root, onefile=args.onefile, windowed=args.windowed
    )

    if not exe_path:
        print("\n❌ Build fallido")
        return 1

    print()

    # Paso 3: Generar hash del instalador
    file_hash, hash_file = generate_installer_hash(exe_path)

    if not file_hash:
        print("⚠️ No se pudo generar el hash del instalador")

    print()

    # Paso 4: Crear metadatos del release
    if file_hash:
        metadata_path = create_release_metadata(
            project_root, exe_path, file_hash, args.version
        )

    # Paso 5: Crear guía de verificación
    guide_path = create_verification_guide(project_root)

    # Paso 6: Copiar archivo VERSION
    dist_dir = project_root / "dist"
    copy_version_file(project_root, dist_dir)

    # Resumen
    print()
    print("=" * 60)
    print("✅ Build completado exitosamente!")
    print("=" * 60)
    print()
    print("📦 Archivos generados:")
    print(f"   📄 Ejecutable: {exe_path}")
    if file_hash:
        print(f"   🔑 Hash:       {hash_file}")
    if manifest_path:
        print(f"   📋 Manifest:   {manifest_path}")
    if guide_path:
        print(f"   📖 Guía:       {guide_path}")
    print()
    print("🔐 Verificación:")
    if file_hash:
        print(f"   SHA-256: {file_hash}")
    print()
    print("📌 Siguientes pasos:")
    print("   1. Verifica el ejecutable funciona correctamente")
    print("   2. Sube los archivos de dist/ a GitHub Releases")
    print("   3. Publica el hash SHA-256 en las notas del release")
    print("   4. Incluye VERIFICATION.md para usuarios")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
