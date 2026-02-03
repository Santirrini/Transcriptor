# Guía de Contribución

¡Gracias por tu interés en contribuir a DesktopWhisperTranscriber! Este documento proporciona las directrices y estándares para contribuir al proyecto.

## Tabla de Contenidos

- [Código de Conducta](#código-de-conducta)
- [Cómo Contribuir](#cómo-contribuir)
- [Configuración del Entorno de Desarrollo](#configuración-del-entorno-de-desarrollo)
- [Estándares de Código](#estándares-de-código)
- [Proceso de Pull Requests](#proceso-de-pull-requests)
- [Reportar Bugs](#reportar-bugs)
- [Solicitar Funcionalidades](#solicitar-funcionalidades)
- [Testing](#testing)
- [Seguridad](#seguridad)
- [Comunidad](#comunidad)

## Código de Conducta

Este proyecto sigue un código de conducta básico:
- Sé respetuoso y considerado con todos los contribuidores
- Acepta constructivamente las críticas
- Enfócate en lo que es mejor para la comunidad
- Muestra empatía hacia otros miembros de la comunidad

## Cómo Contribuir

### Reportar Bugs

Antes de crear un issue de bug:
1. Busca en los [issues existentes](https://github.com/anomalyco/Transcriptor/issues) para evitar duplicados
2. Verifica que el bug no sea un problema conocido documentado en [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

Al reportar un bug, usa el template de "Bug Report" e incluye:
- **Descripción clara** del problema
- **Pasos para reproducir** el error
- **Comportamiento esperado** vs **comportamiento actual**
- **Screenshots** (si aplica)
- **Información del sistema** (OS, versión de Python, versión de la app)
- **Logs relevantes** (de la carpeta `logs/`)

### Solicitar Funcionalidades

Para sugerir nuevas funcionalidades:
1. Busca en los [issues existentes](https://github.com/anomalyco/Transcriptor/issues) para ver si ya existe
2. Describe el caso de uso y los beneficios
3. Explica cómo se diferencia de las funcionalidades existentes

### Contribuciones de Código

1. **Fork** el repositorio
2. Crea una **rama** descriptiva (`git checkout -b feature/nueva-funcionalidad`)
3. Realiza tus cambios siguiendo los [estándares de código](#estándares-de-código)
4. **Testea** tus cambios (ver [Testing](#testing))
5. **Commit** tus cambios con mensajes descriptivos
6. **Push** a tu fork
7. Crea un **Pull Request** siguiendo el template

## Configuración del Entorno de Desarrollo

### Requisitos

- Python 3.11 o superior
- Git
- FFmpeg (incluido en el proyecto)
- (Opcional) VS Code o PyCharm

### Pasos de Instalación

1. **Fork y clone** el repositorio:
   ```bash
   git clone https://github.com/TU_USUARIO/Transcriptor.git
   cd Transcriptor
   ```

2. **Crea el entorno virtual**:
   ```bash
   python -m venv whisper_env_py311
   ```

3. **Activa el entorno virtual**:
   - Windows: `whisper_env_py311\Scripts\activate`
   - Linux/macOS: `source whisper_env_py311/bin/activate`

4. **Instala las dependencias**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

5. **Configura pre-commit hooks**:
   ```bash
   pre-commit install
   ```

6. **Verifica la instalación**:
   ```bash
   python -m pytest tests/ -v
   ```

Para más detalles, consulta [DEVELOPMENT.md](DEVELOPMENT.md).

## Estándares de Código

### Python (PEP 8)

- Máximo **100 caracteres** por línea
- Usa **4 espacios** para indentación
- Nombra variables y funciones con `snake_case`
- Nombra clases con `CamelCase`
- Nombra constantes con `UPPER_SNAKE_CASE`
- Usa **type hints** para todos los parámetros y retornos

### Docstrings (Google Style)

Todas las funciones y clases públicas deben tener docstrings:

```python
def mi_funcion(param1: str, param2: int) -> bool:
    """Descripción breve de la función.

    Descripción más detallada si es necesaria.

    Args:
        param1: Descripción del parámetro 1.
        param2: Descripción del parámetro 2.

    Returns:
        Descripción del valor retornado.

    Raises:
        ValueError: Cuándo se lanza esta excepción.
    """
    pass
```

### Comentarios

- Usa comentarios solo cuando el código no es autoexplicativo
- Mantén los comentarios actualizados
- Usa comentarios en español (idioma del proyecto)

### Imports

Orden de imports:
1. Librerías estándar de Python
2. Librerías de terceros
3. Imports del proyecto (con `from src...`)

```python
import os
import sys
from typing import Optional

import customtkinter as ctk
from faster_whisper import WhisperModel

from src.core.transcriber_engine import TranscriberEngine
```

## Proceso de Pull Requests

### Antes de crear un PR

- [ ] Los tests pasan localmente: `pytest tests/ -v`
- [ ] El código sigue los estándares de estilo: `black src/ tests/` y `isort src/ tests/`
- [ ] No hay errores de linting: `flake8 src/ tests/`
- [ ] La seguridad está verificada: `bandit -r src/`
- [ ] La documentación está actualizada (docstrings, README si aplica)
- [ ] Los commits tienen mensajes descriptivos

### Estructura del PR

1. **Título claro**: Prefijo con tipo (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `security:`)
2. **Descripción detallada**:
   - Qué cambios hace este PR
   - Por qué son necesarios
   - Referencias a issues relacionados
3. **Screenshots/GIFs** (si hay cambios visuales)
4. **Checklist de verificación** completado

### Revisión de PR

- Un maintainer revisará tu PR en 3-5 días hábiles
- Responde a los comentarios de revisión
- Haz push de cambios adicionales según sea necesario
- El PR se mergeará cuando:
  - Todos los checks de CI pasen
  - Tenga aprobación de al menos 1 maintainer
  - No haya conflictos con la rama main

## Testing

### Ejecutar Tests

```bash
# Todos los tests
python -m pytest tests/ -v

# Tests específicos
python -m pytest tests/test_transcriber_engine.py -v

# Con coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Escribir Tests

- Usa `pytest` como framework de testing
- Nombra los archivos de test `test_*.py`
- Nombra las funciones de test `test_*`
- Usa fixtures de pytest para setup/teardown
- Cobra al menos 80% de coverage para código nuevo

```python
def test_mi_nueva_funcionalidad():
    """Test que verifica el comportamiento esperado."""
    # Arrange
    input_data = "test"
    
    # Act
    result = mi_funcion(input_data)
    
    # Assert
    assert result == "expected"
```

### Tipos de Tests

- **Unit tests**: Tests individuales de funciones/clases
- **Integration tests**: Tests de interacción entre componentes
- **Security tests**: Tests de validación de seguridad

## Seguridad

La seguridad es una prioridad máxima. Antes de contribuir código:

1. **Nunca** commitees credenciales, tokens o información sensible
2. Valida todas las entradas de usuario
3. Usa consultas parametrizadas (no concatenación de strings)
4. Escapa output que se muestre en UI
5. Consulta la [Guía de Seguridad](docs/SECURITY.md) para más detalles

### Reporte de Vulnerabilidades

Si descubres una vulnerabilidad de seguridad:
1. **NO** crees un issue público
2. Envía un email a [INSERTAR EMAIL] con detalles
3. Espera respuesta antes de divulgar públicamente

## Comunidad

### Canales de Comunicación

- **GitHub Issues**: Para bugs y features
- **GitHub Discussions**: Para preguntas y discusiones generales
- **Pull Requests**: Para revisión de código

### Reconocimiento

Los contribuidores serán reconocidos en:
- Archivo `CONTRIBUTORS.md`
- Release notes
- README principal

### Dónde Obtener Ayuda

- Lee la [documentación completa](docs/)
- Consulta [TROUBLESHOOTING.md](TROUBLESHOOTING.md) para problemas comunes
- Revisa los [issues cerrados](https://github.com/anomalyco/Transcriptor/issues?q=is%3Aissue+is%3Aclosed) para soluciones previas
- Participa en GitHub Discussions

---

## Checklist de Calidad

Antes de enviar cualquier contribución, verifica:

- [ ] El código compila y ejecuta sin errores
- [ ] Todos los tests pasan
- [ ] No hay warnings de linting
- [ ] La documentación está actualizada
- [ ] Los mensajes de commit son descriptivos
- [ ] No se incluyen archivos innecesarios (logs, archivos temporales)
- [ ] La seguridad está verificada (bandit)

---

¡Gracias por contribuir a hacer DesktopWhisperTranscriber mejor!
