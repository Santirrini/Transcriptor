# Guía de Troubleshooting

Esta guía te ayuda a resolver problemas comunes con DesktopWhisperTranscriber.

## Tabla de Contenidos

- [Problemas de Instalación](#problemas-de-instalación)
- [Problemas de Ejecución](#problemas-de-ejecución)
- [Problemas con FFmpeg](#problemas-con-ffmpeg)
- [Problemas de Transcripción](#problemas-de-transcripción)
- [Problemas con YouTube](#problemas-con-youtube)
- [Problemas de Diarización](#problemas-de-diarización)
- [Problemas de Memoria/Rendimiento](#problemas-de-memoriarendimiento)
- [Errores de Seguridad](#errores-de-seguridad)
- [Cómo Reportar Problemas](#cómo-reportar-problemas)

---

## Problemas de Instalación

### "Python no está instalado o no está en el PATH"

**Síntoma**: Al ejecutar `run.bat`, aparece "Python no encontrado"

**Solución**:
1. Descarga Python 3.11 desde [python.org](https://python.org)
2. Durante la instalación, marca "Add Python to PATH"
3. Reinicia la terminal/cmd
4. Verifica: `python --version`

### "No se puede crear el entorno virtual"

**Síntoma**: Error al crear `whisper_env_py311`

**Solución**:
```cmd
# Elimina el entorno corrupto (si existe)
rmdir /s whisper_env_py311

# Reinstala virtualenv
python -m pip install --upgrade virtualenv

# Crea el entorno nuevamente
python -m venv whisper_env_py311
```

### Error al instalar dependencias

**Síntoma**: `pip install` falla con errores de compilación

**Solución**:
1. Actualiza pip: `python -m pip install --upgrade pip`
2. Instala build tools de Windows: [Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)
3. Para error con torch: instala manualmente desde [pytorch.org](https://pytorch.org)

---

## Problemas de Ejecución

### "No module named 'src'"

**Síntoma**: ImportError al ejecutar la aplicación

**Solución**:
- Nunca ejecutes archivos individuales dentro de `src/`
- Siempre usa: `python src/main.py` desde el directorio raíz
- O usa el script `run.bat`/`run.sh`

### La aplicación no inicia (pantalla negra o se cierra)

**Síntoma**: La ventana aparece brevemente y se cierra

**Solución**:
1. Verifica logs en `logs/app.log`
2. Verifica que el modelo Whisper se descargó correctamente
3. Borra la caché: elimina carpeta `~/.cache/whisper/`
4. Reinstala dependencias: `pip install -r requirements.txt --force-reinstall`

### Error de inicialización del motor

**Síntoma**: "No se pudo cargar el modelo de transcripción"

**Causa**: Falta de memoria RAM o VRAM insuficiente

**Solución**:
- Usa un modelo más pequeño (tiny/base en lugar de large)
- Cierra otras aplicaciones para liberar RAM
- Si usas GPU, verifica que tiene suficiente VRAM (4GB+ para medium, 10GB+ para large)

---

## Problemas con FFmpeg

### "FFmpeg no encontrado"

**Síntoma**: Error al procesar archivos de audio

**Solución**:
1. Verifica que FFmpeg está en `C:\Users\Jose Diaz\Documents\Transcriptor\ffmpeg\`
2. Verifica que el PATH se configura correctamente (el script `run.bat` lo hace automáticamente)
3. Manualmente, agrega al PATH: `C:\Users\Jose Diaz\Documents\Transcriptor\ffmpeg\`

### FFmpeg falla al procesar archivo específico

**Síntoma**: Error al convertir cierto formato de audio

**Solución**:
- Verifica que el archivo no esté corrupto: `ffprobe -i archivo.mp3`
- Convierte el archivo manualmente: `ffmpeg -i archivo.mp3 -ar 16000 output.wav`
- Intenta con otro formato (WAV es el más compatible)

---

## Problemas de Transcripción

### Transcripción es muy lenta

**Síntoma**: El progreso avanza muy despacio

**Soluciones**:
1. **Usa un modelo más pequeño**: Cambia de "large" a "medium" o "base"
2. **Usa GPU**: Asegúrate de tener CUDA instalado y `torch` con soporte GPU
3. **Reduce la calidad**: En la UI, selecciona calidad menor
4. **Verifica CPU**: Si no tienes GPU, transcripción en CPU es intrínsecamente lenta

### La transcripción se congela/deteniene

**Síntoma**: Barra de progreso se detiene

**Solución**:
1. Verifica logs: `logs/app.log` y `logs/errors/`
2. Cancela y reintenta (botón "Cancelar")
3. Verifica que no haya otros programas usando mucha CPU/GPU
4. Para archivos muy grandes, usa procesamiento por fragmentos

### Texto transcrito es de baja calidad

**Síntoma**: Muchos errores en el texto

**Soluciones**:
1. **Mejora la calidad del audio**: Elimina ruido de fondo
2. **Usa modelo más grande**: Cambia a "medium" o "large"
3. **Audio claro**: Asegúrate de que el hablante esté cerca del micrófono
4. **Idioma correcto**: Verifica que el idioma seleccionado coincida con el audio

### Error "Audio file is too long"

**Síntoma**: Archivo de audio excede el límite

**Solución**:
- Habilita "Procesar por fragmentos" en la interfaz
- El archivo se dividirá automáticamente en segmentos manejables
- Los fragmentos se concatenan al final

### Error de memoria "Out of memory"

**Síntoma**: Error de RAM o GPU memory

**Soluciones**:
1. Reinicia la aplicación
2. Usa modelo más pequeño
3. Cierra otras aplicaciones
4. Habilita procesamiento por fragmentos
5. Si tienes GPU, verifica que torch.use_cuda() esté funcionando correctamente

---

## Problemas con YouTube

### "Error al descargar video de YouTube"

**Síntoma**: Falla al procesar URL de YouTube

**Soluciones**:
1. **Verifica la URL**: Debe ser una URL válida de YouTube (ej: `https://www.youtube.com/watch?v=...`)
2. **Video privado/restringido**: La aplicación no puede descargar videos privados
3. **Video muy largo**: Para videos > 2 horas, puede fallar por timeout
4. **Cambia el método**: Intenta con `yt-dlp` manualmente:
   ```bash
   yt-dlp -x --audio-format mp3 "URL" -o audio.mp3
   ```

### Video de YouTube no tiene audio

**Síntoma**: Descarga exitosa pero sin audio

**Solución**:
- Algunos videos no tienen stream de audio disponible
- Intenta descargar el video completo y extraer audio después
- Usa formato diferente (puede que opus no funcione, prueba m4a)

### Error 403 Forbidden

**Síntoma**: Acceso denegado al descargar

**Solución**:
- YouTube bloqueó el request temporalmente
- Espera unos minutos e intenta nuevamente
- Usa cookies de navegador: crea archivo `cookies.txt`

---

## Problemas de Diarización

### "Error al inicializar diarización"

**Síntoma**: Falla al activar "Identificar hablantes"

**Soluciones**:
1. **HuggingFace Token**: Verifica que tu token es válido en https://huggingface.co/settings/tokens
2. **Acepta el acuerdo**: Debes aceptar los términos del modelo en HuggingFace
3. **Modelo**: pyannote/speaker-diarization requiere aceptar términos específicos
4. **Conexión**: Verifica conexión a internet para descargar el modelo

### Diarización es incorrecta

**Síntoma**: Identifica mal los hablantes

**Nota**: La diarización automática tiene limitaciones:
- Funciona mejor con audio claro y poco ruido
- 2-4 hablantes es el rango óptimo
- Voces muy similares pueden confundirse
- Audio de baja calidad reduce precisión

---

## Problemas de Memoria/Rendimiento

### La aplicación consume mucha RAM

**Síntoma**: Sistema se vuelve lento

**Soluciones**:
1. Usa modelo Whisper más pequeño
2. Procesa archivos en fragmentos
3. Cierra la aplicación entre transcripciones (el modelo se mantiene en memoria)
4. Verifica que no haya fugas de memoria en logs

### GPU no se utiliza

**Síntoma**: Transcripción lenta a pesar de tener GPU

**Verificación**:
```python
import torch
print(torch.cuda.is_available())  # Debe ser True
print(torch.cuda.device_count())  # Debe ser >= 1
```

**Solución**:
1. Instala torch con soporte CUDA:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   ```
2. Verifica drivers de NVIDIA actualizados
3. En la UI, verifica que "Usar GPU" esté habilitado

---

## Errores de Seguridad

### "Validación de seguridad fallida"

**Síntoma**: Error al cargar archivo o procesar URL

**Causa**: El sistema de seguridad detectó algo potencialmente peligroso

**Solución**:
1. Verifica que el archivo/URL sea legítimo
2. Si es un falso positivo, reporta el issue con logs
3. Verifica el hash del archivo si es descargado

### Error de integridad de archivo

**Síntoma**: "Checksum verification failed"

**Solución**:
- El archivo puede estar corrupto
- Descarga nuevamente desde fuente confiable
- Verifica que no haya sido modificado por malware

---

## Cómo Reportar Problemas

Si no encuentras tu problema aquí:

1. **Revisa los logs**:
   - `logs/app.log` - Log general
   - `logs/errors/` - Errores específicos
   - `logs/security_audit.jsonl` - Logs de seguridad

2. **Verifica issues existentes**: Busca en [GitHub Issues](https://github.com/anomalyco/Transcriptor/issues)

3. **Crea un nuevo issue** usando el template "Bug Report" e incluye:
   - Descripción del problema
   - Pasos para reproducir
   - Logs relevantes
   - Información del sistema (OS, versión Python, versión app)
   - Screenshots si aplica

4. **Para problemas de seguridad**: NO crees issue público, envía email a [INSERTAR EMAIL]

---

## Recursos Adicionales

- [README principal](README.md)
- [Guía de contribución](CONTRIBUTING.md)
- [Desarrollo](DEVELOPMENT.md)
- [Documentación completa](docs/)

---

## Errores Comunes y Códigos

| Código | Descripción | Solución Rápida |
|--------|-------------|-----------------|
| E001 | Modelo no encontrado | Reinstala dependencias |
| E002 | FFmpeg no disponible | Verifica PATH de FFmpeg |
| E003 | Out of memory | Usa modelo más pequeño o fragmentos |
| E004 | URL inválida | Verifica formato de URL |
| E005 | Token HF inválido | Regenera token en HuggingFace |
| E006 | Archivo corrupto | Verifica/re-descarga archivo |
| E007 | Timeout de red | Verifica conexión, reintenta |
| E008 | Permiso denegado | Ejecuta como administrador |

---

**¿Sigues teniendo problemas?** Únete a nuestras [GitHub Discussions](https://github.com/anomalyco/Transcriptor/discussions) para obtener ayuda de la comunidad.
