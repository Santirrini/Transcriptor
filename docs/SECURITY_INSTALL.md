# 🔐 Guía de Instalación Segura - DesktopWhisperTranscriber

Esta guía te ayuda a instalar DesktopWhisperTranscriber de forma segura, verificando la integridad de los archivos descargados.

## 📥 Descarga

1. **Siempre descarga desde GitHub Releases oficial:**
   - URL: https://github.com/JoseDiazCodes/DesktopWhisperTranscriber/releases
   - Nunca descargues desde sitios de terceros

2. **Archivos que necesitas:**
   - `DesktopWhisperTranscriber.exe` (o `.zip` para Windows)
   - `DesktopWhisperTranscriber.exe.sha256` (hash de verificación)
   - `release_metadata.json` (metadatos del release)

## ✅ Verificación de Integridad

Es **muy importante** verificar que el archivo descargado no ha sido modificado. Sigue estos pasos:

### Windows - PowerShell (Recomendado)

1. Abre PowerShell en la carpeta donde descargaste el archivo
2. Ejecuta:

```powershell
Get-FileHash DesktopWhisperTranscriber.exe -Algorithm SHA256
```

3. Compara el resultado con el contenido del archivo `.sha256`

### Windows - Command Prompt (cmd)

1. Abre Command Prompt en la carpeta de descargas
2. Ejecuta:

```cmd
certutil -hashfile DesktopWhisperTranscriber.exe SHA256
```

3. Compara el hash mostrado con el del archivo `.sha256`

### macOS / Linux

```bash
sha256sum DesktopWhisperTranscriber.exe
```

### Comparación Manual

1. Abre el archivo `DesktopWhisperTranscriber.exe.sha256` con un editor de texto
2. Deberías ver algo como:
   ```
   abc123def456...789  DesktopWhisperTranscriber.exe
   ```
3. El hash generado por los comandos anteriores debe **coincidir exactamente**

## 🚨 Si el hash NO coincide

⚠️ **NO instales la aplicación** si el hash no coincide. Esto podría indicar:

- El archivo se corrompió durante la descarga
- El archivo fue modificado por un tercero (potencialmente malicioso)
- Descargaste desde una fuente no oficial

**Acciones recomendadas:**
1. Descarga el archivo nuevamente desde GitHub
2. Verifica tu conexión a internet
3. Reporta el problema en: https://github.com/JoseDiazCodes/DesktopWhisperTranscriber/issues

## 🛡️ Durante la Instalación

### Windows

1. **Desbloquear archivo** (si Windows lo bloqueó):
   - Click derecho en el archivo → Propiedades
   - Marca "Desbloquear" al final de la ventana (si aparece)
   - Click en Aceptar

2. **Ejecutar**:
   - Doble click en `DesktopWhisperTranscriber.exe`
   - Si Windows SmartScreen aparece:
     - Click en "Más información"
     - Click en "Ejecutar de todos modos"
     - *Nota: Esto es normal para aplicaciones no firmadas digitalmente*

3. **Permisos**:
   - La aplicación necesita permisos para:
     - Acceder a archivos de audio (para transcripción)
     - Conexión a internet (para descargar videos de YouTube)
     - Acceso a Hugging Face (para diarización de hablantes)

### Desde Código Fuente (Desarrolladores)

Si prefieres ejecutar desde el código fuente:

1. **Clonar repositorio**:
   ```bash
   git clone https://github.com/JoseDiazCodes/DesktopWhisperTranscriber.git
   cd DesktopWhisperTranscriber
   ```

2. **Verificar integridad del código**:
   ```bash
   # El manifest debe estar presente
   python -c "from src.core.integrity_checker import integrity_checker; integrity_checker.verify_integrity()"
   ```

3. **Instalar dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecutar**:
   ```bash
   python src/main.py
   ```

## 🔒 Después de la Instalación

### Verificación Automática

La aplicación incluye verificaciones automáticas de seguridad:

1. **Al iniciar**: Verifica que existan los archivos críticos
2. **En tiempo de ejecución**: Valida todas las entradas del usuario
3. **Periódicamente**: Verifica actualizaciones disponibles (solo si está habilitado)

### Configuración de Seguridad Recomendada

1. **Configurar token de Hugging Face** (solo si usas diarización):
   ```bash
   set HUGGING_FACE_HUB_TOKEN=tu_token_aqui
   ```
   - Nunca compartas este token
   - La aplicación lo enmascara en los logs automáticamente

2. **Habilitar actualizaciones automáticas**:
   - Ve a Configuración → Actualizaciones
   - Habilita "Buscar actualizaciones automáticamente"
   - Esto te notificará sobre parches de seguridad importantes

## 📋 Lista de Verificación Pre-Instalación

- [ ] Descargado desde GitHub Releases oficial
- [ ] Verificado hash SHA-256 del ejecutable
- [ ] Hash coincide con el publicado en el release
- [ ] Archivo no bloqueado por antivirus (falso positivo)
- [ ] Sistema operativo compatible (Windows 10/11, Linux, macOS)

## 🆘 Solución de Problemas

### "Windows protegió tu PC" / SmartScreen

**Causa**: Windows no reconoce la aplicación porque no está firmada digitalmente con un certificado comercial.

**Solución**:
1. Click en "Más información"
2. Click en "Ejecutar de todos modos"
3. *Opcional*: Agregar excepción en Windows Defender

### Antivirus detecta como amenaza

**Causa**: Algunos antivirus pueden detectar falsos positivos en aplicaciones de Python empaquetadas.

**Solución**:
1. Verifica el hash SHA-256 primero
2. Si coincide, es seguro agregar una excepción
3. Reporta el falso positivo al fabricante del antivirus

### "Archivo crítico faltante" al iniciar

**Causa**: La instalación está incompleta o corrupta.

**Solución**:
1. Reinstala la aplicación
2. Descarga nuevamente desde GitHub
3. Verifica que tu antivirus no haya eliminado archivos

## 📝 Reportar Problemas de Seguridad

Si encuentras algún problema de seguridad:

1. **NO abras un issue público** para vulnerabilidades graves
2. Contacta directamente al desarrollador
3. Incluye:
   - Versión de la aplicación
   - Sistema operativo
   - Descripción del problema
   - Pasos para reproducir (si aplica)

## 📚 Recursos Adicionales

- **README**: Información general de la aplicación
- **CHANGELOG**: Historial de cambios y actualizaciones de seguridad
- **GitHub Issues**: Reportar bugs y solicitar features
- **GitHub Security**: Políticas de seguridad del proyecto

---

## ⚖️ Descargo de Responsabilidad

DesktopWhisperTranscriber es software de código abierto proporcionado "tal cual", sin garantías de ningún tipo. Siempre verifica la integridad de los archivos descargados y mantén tu sistema actualizado.

**Última actualización**: 2024
**Versión de la guía**: 1.0
