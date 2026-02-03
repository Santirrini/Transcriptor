# Guía de Desarrollo

Guía completa para configurar el entorno de desarrollo de DesktopWhisperTranscriber.

## Tabla de Contenidos

- [Requisitos del Sistema](#requisitos-del-sistema)
- [Instalación del Entorno](#instalación-del-entorno)
- [Configuración del IDE](#configuración-del-ide)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Flujo de Trabajo](#flujo-de-trabajo)
- [Testing](#testing)
- [Debugging](#debugging)
- [Herramientas de Calidad](#herramientas-de-calidad)
- [CI/CD](#cicd)
- [Consejos y Buenas Prácticas](#consejos-y-buenas-prácticas)

---

## Requisitos del Sistema

### Mínimos
- **OS**: Windows 10/11, macOS 10.15+, o Linux (Ubuntu 20.04+)
- **Python**: 3.11 o superior
- **RAM**: 8 GB (16 GB recomendado)
- **Disco**: 5 GB libres (para modelos y dependencias)
- **Git**: 2.30 o superior

### Recomendados (para desarrollo)
- **RAM**: 16 GB o más
- **GPU**: NVIDIA con 4GB+ VRAM (para testing de transcripción rápida)
- **CPU**: Multi-core (para tests paralelos)
- **IDE**: VS Code o PyCharm

---

## Instalación del Entorno

### 1. Fork y Clone

```bash
# Fork el repositorio en GitHub primero

# Luego clona tu fork
git clone https://github.com/TU_USUARIO/Transcriptor.git
cd Transcriptor

# Agrega el upstream original
git remote add upstream https://github.com/anomalyco/Transcriptor.git
```

### 2. Entorno Virtual

```bash
# Crear entorno virtual
python -m venv whisper_env_py311

# Activar entorno virtual
# Windows:
whisper_env_py311\Scripts\activate

# Linux/macOS:
source whisper_env_py311/bin/activate

# Verificar que está activado (debe mostrar la ruta del venv)
which python
```

### 3. Instalación de Dependencias

```bash
# Actualizar pip
python -m pip install --upgrade pip

# Instalar dependencias principales
pip install -r requirements.txt

# Instalar dependencias de desarrollo
pip install -r requirements-dev.txt
```

**Contenido típico de `requirements-dev.txt`**:
```
pytest>=7.0.0
pytest-cov>=4.0.0
black>=23.0.0
isort>=5.12.0
flake8>=6.0.0
mypy>=1.0.0
pre-commit>=3.0.0
bandit>=1.7.0
```

### 4. Configuración de FFmpeg

FFmpeg ya está incluido en el proyecto (`ffmpeg/`).

```bash
# Windows - el script run.bat configura PATH automáticamente
# Manualmente, agrega a PATH:
C:\Users\Jose Diaz\Documents\Transcriptor\ffmpeg

# Verificar instalación
ffmpeg -version
```

### 5. Pre-commit Hooks

```bash
# Instalar hooks
pre-commit install

# Verificar que funcionan
pre-commit run --all-files
```

**Configuración de `.pre-commit-config.yaml`**:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.7.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        args: ["--profile", "black"]

  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        additional_dependencies: [flake8-docstrings]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.5.1
    hooks:
      - id: mypy
        additional_dependencies: [types-requests]
```

### 6. Verificación de Instalación

```bash
# Ejecutar tests
python -m pytest tests/ -v

# Verificar formato de código
black src/ tests/ --check
isort src/ tests/ --check-only
flake8 src/ tests/

# Verificar seguridad
bandit -r src/

# Ejecutar aplicación
python src/main.py
```

---

## Configuración del IDE

### VS Code

#### Extensiones Recomendadas
- Python (Microsoft)
- Pylance
- Python Test Explorer
- Python Docstring Generator
- autoDocstring
- Black Formatter
- isort
- Flake8
- Bandit

#### Configuración (`settings.json`)

```json
{
  "python.defaultInterpreterPath": "./whisper_env_py311/Scripts/python.exe",
  "python.analysis.typeCheckingMode": "basic",
  "python.analysis.autoImportCompletions": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.linting.banditEnabled": true,
  "python.sortImports.args": ["--profile", "black"],
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests", "-v"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

#### Launch Configuration (`launch.json`)

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "DesktopWhisperTranscriber",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/src/main.py",
      "console": "integratedTerminal",
      "cwd": "${workspaceFolder}",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal"
    },
    {
      "name": "Pytest: Current File",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["${file}", "-v"],
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm

#### Configuración de Proyecto
1. **File > Settings > Project > Python Interpreter**
   - Selecciona el entorno virtual `whisper_env_py311`

2. **File > Settings > Tools > Python Integrated Tools**
   - Testing: pytest
   - Docstring format: Google

3. **Run/Debug Configurations**
   - Script path: `src/main.py`
   - Working directory: Raíz del proyecto

#### Atajos Útiles
- `Ctrl+Alt+L`: Reformat code (Black)
- `Ctrl+Shift+T`: Go to test
- `Shift+F10`: Run
- `Shift+F9`: Debug

---

## Estructura del Proyecto

```
DesktopWhisperTranscriber/
├── src/                          # Código fuente
│   ├── main.py                   # Punto de entrada
│   ├── core/                     # Lógica de negocio
│   │   ├── transcriber_engine.py
│   │   ├── audio_handler.py
│   │   ├── chunk_processor.py
│   │   ├── diarization_handler.py
│   │   ├── model_manager.py
│   │   ├── exporter.py
│   │   ├── validators.py
│   │   ├── logger.py
│   │   ├── audit_logger.py
│   │   ├── integrity_checker.py
│   │   ├── update_checker.py
│   │   └── exceptions.py
│   └── gui/                      # Interfaz gráfica
│       ├── main_window.py
│       ├── theme/
│       ├── utils/
│       └── components/
├── tests/                        # Tests
│   ├── test_*.py
│   └── fixtures/
├── docs/                         # Documentación
├── memory-bank/                  # Decisiones arquitectónicas
├── ffmpeg/                       # Binarios FFmpeg
├── logs/                         # Logs de aplicación
├── requirements.txt              # Dependencias
├── requirements-dev.txt          # Dependencias de desarrollo
├── run.bat                       # Script Windows
├── run.sh                        # Script Linux/macOS
├── .pre-commit-config.yaml       # Hooks de pre-commit
├── pyproject.toml               # Configuración de herramientas
└── README.md
```

---

## Flujo de Trabajo

### Branching Strategy

Usamos **GitHub Flow** (simplificado):

```bash
# 1. Asegúrate de tener la última versión
git checkout main
git pull upstream main
git push origin main

# 2. Crea una rama para tu feature
# Formatos: feature/descripcion, fix/descripcion, docs/descripcion
git checkout -b feature/mi-nueva-funcionalidad

# 3. Haz commits con mensajes descriptivos
git add .
git commit -m "feat: agrega soporte para formato X"

# 4. Push a tu fork
git push origin feature/mi-nueva-funcionalidad

# 5. Crea Pull Request en GitHub
```

### Convención de Commits

Formato: `tipo(alcance): descripción`

Tipos:
- `feat`: Nueva funcionalidad
- `fix`: Corrección de bug
- `docs`: Documentación
- `style`: Cambios de formato (espacios, punto y coma)
- `refactor`: Refactorización de código
- `test`: Tests
- `chore`: Tareas de mantenimiento
- `security`: Mejoras de seguridad

Ejemplos:
```
feat(transcription): agrega soporte para archivos OGG
fix(gui): corrige memory leak en ventana principal
docs(readme): actualiza instrucciones de instalación
test(engine): agrega tests para chunked processing
security(validators): mejora validación de URLs
```

---

## Testing

### Ejecutar Tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Tests específicos
python -m pytest tests/test_transcriber_engine.py -v

# Tests con coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
python -m pytest tests/ --cov=src --cov-report=html
# Ver reporte: htmlcov/index.html

# Tests en paralelo (más rápido)
python -m pytest tests/ -n auto

# Solo tests de integración
python -m pytest tests/ -m integration

# Solo tests unitarios
python -m pytest tests/ -m unit
```

### Escribir Tests

```python
import pytest
from src.core.transcriber_engine import TranscriberEngine

class TestTranscriberEngine:
    """Tests para el motor de transcripción."""
    
    @pytest.fixture
    def engine(self):
        """Fixture que provee una instancia del motor."""
        return TranscriberEngine(model_size="tiny")
    
    def test_initialization(self, engine):
        """Test que el motor se inicializa correctamente."""
        assert engine is not None
        assert engine.model is not None
    
    def test_transcribe_empty_raises_error(self, engine):
        """Test que transcribir archivo vacío lanza error."""
        with pytest.raises(ValueError):
            engine.transcribe("")
```

### Mocking

```python
from unittest.mock import Mock, patch, MagicMock

@patch('src.core.audio_handler.FFmpeg')
def test_audio_conversion(mock_ffmpeg):
    """Test con mocking de FFmpeg."""
    mock_instance = MagicMock()
    mock_ffmpeg.return_value = mock_instance
    
    # Tu test aquí
    result = audio_handler.convert("input.mp3")
    
    mock_instance.run.assert_called_once()
```

---

## Debugging

### Debugging en VS Code

1. Pon breakpoints haciendo clic en el margen izquierdo
2. Presiona `F5` o usa el menú Debug > Start Debugging
3. Usa el panel de debugging:
   - **Variables**: Inspecciona variables
   - **Watch**: Monitorea expresiones específicas
   - **Call Stack**: Pila de llamadas
   - **Debug Console**: Evalúa expresiones Python

### Debugging de Threads

La aplicación usa threading para transcripción. Para debuggear:

```python
import threading
import logging

# Agrega logs de threading
logging.basicConfig(
    level=logging.DEBUG,
    format='%(threadName)s: %(message)s'
)

# O usa threading.current_thread()
print(f"Current thread: {threading.current_thread().name}")
```

### Logs en Desarrollo

```python
from src.core.logger import logger

# En tu código
logger.debug("Mensaje de debug")
logger.info("Información")
logger.warning("Advertencia")
logger.error("Error")

# Logs se guardan en: logs/app.log
```

### Debugging de GUI

```python
import tkinter as tk

# Para inspeccionar widgets
print(app.winfo_children())

# Para debuggear eventos
app.bind_all("<Key>", lambda e: print(f"Key pressed: {e.keysym}"))
```

---

## Herramientas de Calidad

### Black (Formateo)

```bash
# Formatear todo
black src/ tests/

# Verificar sin cambiar
black src/ tests/ --check

# Ver diff
black src/ tests/ --diff
```

### isort (Ordenar imports)

```bash
# Organizar imports
isort src/ tests/

# Verificar
isort src/ tests/ --check-only
```

### Flake8 (Linting)

```bash
# Ejecutar flake8
flake8 src/ tests/

# Ignorar ciertos errores
flake8 src/ tests/ --ignore=E501,W503
```

### MyPy (Type Checking)

```bash
# Verificar tipos
mypy src/

# Ignorar módulos sin types
mypy src/ --ignore-missing-imports
```

### Bandit (Seguridad)

```bash
# Análisis de seguridad
bandit -r src/

# Solo errores de severidad alta
bandit -r src/ -lll

# Generar reporte JSON
bandit -r src/ -f json -o bandit-report.json
```

### Todos juntos (Script)

```bash
#!/bin/bash
# quality-check.sh

echo "Running Black..."
black src/ tests/ --check || exit 1

echo "Running isort..."
isort src/ tests/ --check-only || exit 1

echo "Running Flake8..."
flake8 src/ tests/ || exit 1

echo "Running MyPy..."
mypy src/ || exit 1

echo "Running Bandit..."
bandit -r src/ -lll || exit 1

echo "Running Tests..."
python -m pytest tests/ -v || exit 1

echo "All quality checks passed!"
```

---

## CI/CD

El proyecto usa GitHub Actions. Los workflows están en `.github/workflows/`.

### Workflows Principales

1. **CI**: Tests, linting, seguridad en cada PR
2. **Release**: Generación de ejecutables y assets
3. **Security**: Análisis de seguridad con Bandit

### Ejecutar CI localmente

```bash
# Instalar act (runner local de GitHub Actions)
brew install act  # macOS
# o descarga desde https://github.com/nektos/act

# Ejecutar workflow
act push
act pull_request
```

---

## Consejos y Buenas Prácticas

### Performance

1. **Lazy Loading**: Carga modelos solo cuando se necesitan
2. **Caching**: Cache resultados de operaciones costosas
3. **Chunking**: Procesa archivos grandes en fragmentos
4. **Threading**: Usa threads para operaciones I/O bound

### Seguridad

1. Nunca hardcodees credenciales
2. Valida todas las entradas
3. Usa consultas parametrizadas
4. Escapa output en UI
5. Revisa logs con Bandit regularmente

### Testing

1. Escribe tests antes que código (TDD)
2. Mantén coverage > 80%
3. Usa fixtures para setup/teardown
4. Mockea operaciones costosas (I/O, red)
5. Tests independientes (no dependan de orden)

### Código

1. Funciones pequeñas (< 50 líneas)
2. Un propósito por función
3. Nombres descriptivos
4. Type hints en todo
5. Docstrings en todo lo público

### Git

1. Commits atómicos (un cambio lógico por commit)
2. Mensajes descriptivos
3. Pull requests pequeños (< 500 líneas)
4. Rebase antes de merge para historial limpio
5. No commitees archivos generados (logs, __pycache__)

---

## Recursos

### Documentación
- [README principal](README.md)
- [Guía de contribución](CONTRIBUTING.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Documentación completa](docs/)

### Enlaces útiles
- [PEP 8](https://pep8.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [pytest documentation](https://docs.pytest.org/)
- [Black documentation](https://black.readthedocs.io/)
- [CustomTkinter docs](https://github.com/TomSchimansky/CustomTkinter/wiki)
- [faster-whisper docs](https://github.com/SYSTRAN/faster-whisper)

---

## Soporte

- **Issues**: [GitHub Issues](https://github.com/anomalyco/Transcriptor/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anomalyco/Transcriptor/discussions)
- **Email**: [INSERTAR EMAIL]

---

¡Feliz desarrollo! 🚀
