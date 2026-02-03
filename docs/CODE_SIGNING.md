# 🔏 Guía de Firma de Código (Code Signing)

Esta guía explica cómo configurar la firma de código para DesktopWhisperTranscriber, eliminando las advertencias de Windows SmartScreen y aumentando la confianza de los usuarios.

## 📋 Índice

1. [¿Qué es la firma de código?](#qué-es-la-firma-de-código)
2. [Beneficios](#beneficios)
3. [Opciones de certificados](#opciones-de-certificados)
4. [Proceso de adquisición](#proceso-de-adquisición)
5. [Configuración en Windows](#configuración-en-windows)
6. [Integración con el build](#integración-con-el-build)
7. [Verificación de la firma](#verificación-de-la-firma)
8. [Consideraciones de costo](#consideraciones-de-costo)
9. [Alternativas gratuitas](#alternativas-gratuitas)

## 🔍 ¿Qué es la Firma de Código?

La firma de código es un certificado digital que:
- ✅ Verifica la identidad del desarrollador/publisher
- ✅ Garantiza que el código no ha sido modificado desde la firma
- ✅ Elimina advertencias de "Windows protegió tu PC" (SmartScreen)
- ✅ Muestra el nombre del publisher en lugar de "Desconocido"

## 🎯 Beneficios

### Para el Usuario:
- ✅ Sin advertencias de seguridad al instalar
- ✅ Confianza verificada del publisher
- ✅ Protección contra modificaciones maliciosas

### Para el Desarrollador:
- ✅ Mayor tasa de instalaciones completadas
- ✅ Imagen profesional y confiable
- ✅ Protección de marca

## 📜 Opciones de Certificados

### 1. **OV (Organization Validation)** - Recomendado para empezar
- **Costo**: ~$200-500 USD/año
- **Validación**: Verificación de empresa/organización
- **Tiempo**: 1-3 días hábiles
- **Proveedores**: DigiCert, Sectigo, SSL.com
- **Ideal para**: Desarrolladores individuales o pequeñas empresas

### 2. **EV (Extended Validation)** - Máxima confianza
- **Costo**: ~$600-800 USD/año
- **Validación**: Verificación exhaustiva de identidad legal
- **Tiempo**: 3-7 días hábiles
- **Proveedores**: DigiCert, Sectigo
- **Ideal para**: Empresas establecidas, software empresarial
- **Beneficio adicional**: Inmediata reputación en SmartScreen

### 3. **Certificado Individual**
- **Costo**: ~$200-400 USD/año
- **Validación**: Verificación de identidad personal
- **Ideal para**: Desarrolladores independientes sin empresa

## 🛒 Proceso de Adquisición

### Paso 1: Elegir Proveedor

**Opciones recomendadas:**

1. **Sectigo** (anteriormente Comodo)
   - Website: https://sectigo.com
   - Precio: ~$200-400/año
   - Buena reputación, fácil proceso

2. **DigiCert**
   - Website: https://digicert.com
   - Precio: ~$400-800/año
   - Premium, excelente soporte

3. **SSL.com**
   - Website: https://ssl.com
   - Precio: ~$200-300/año
   - Opción económica confiable

### Paso 2: Solicitar Certificado

1. Crear cuenta en el proveedor elegido
2. Seleccionar "Code Signing Certificate"
3. Elegir tipo (OV o EV)
4. Completar el proceso de pago

### Paso 3: Validación

**Para OV:**
- Verificación de identidad (pasaporte/DNI)
- Verificación de dirección (factura de servicios)
- Posible verificación telefónica

**Para EV:**
- Todo lo de OV más:
- Verificación legal de la empresa
- Verificación de operación comercial
- Entrevista telefónica más detallada

### Paso 4: Recibir Certificado

- El certificado se emite en formato PFX/P12
- Se enviará por email con instrucciones de instalación
- **¡Importante!** Guardar la contraseña del certificado de forma segura

## ⚙️ Configuración en Windows

### Paso 1: Instalar el Certificado

**Método 1: Instalación automática (PFX)**
```powershell
# Doble click en el archivo .pfx
# Seguir el asistente de importación
# Seleccionar "Máquina local" (Local Machine)
# Guardar en "Personal" (Personal)
```

**Método 2: Línea de comandos**
```powershell
# Abrir PowerShell como administrador
certutil -importpfx "C:\path\to\certificate.pfx"
```

### Paso 2: Verificar Instalación

```powershell
# Listar certificados en el almacén personal
Get-ChildItem -Path Cert:\LocalMachine\My

# O usando certmgr.msc (GUI)
certmgr.msc
```

### Paso 3: Extraer Información del Certificado

```powershell
# Obtener thumbprint del certificado
$cert = Get-ChildItem -Path Cert:\LocalMachine\My | Where-Object { $_.Subject -like "*Your Company*" }
$thumbprint = $cert.Thumbprint
Write-Output "Thumbprint: $thumbprint"
```

## 🔨 Integración con el Build

### Opción 1: Usar signtool.exe (Windows SDK)

**Requisitos:**
- Windows SDK instalado (incluye signtool.exe)
- Normalmente en: `C:\Program Files (x86)\Windows Kits\10\bin\10.0.xxxxx.x\x64\signtool.exe`

**Script de firma:**
```powershell
# firmar.ps1
param(
    [Parameter(Mandatory=$true)]
    [string]$ExePath,
    
    [Parameter(Mandatory=$true)]
    [string]$Thumbprint
)

$signtool = "C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe"

# Firmar el ejecutable
& $signtool sign `
    /sha1 $Thumbprint `
    /tr http://timestamp.sectigo.com `
    /td sha256 `
    /fd sha256 `
    /a `
    "$ExePath"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Firma exitosa" -ForegroundColor Green
} else {
    Write-Host "❌ Error en la firma" -ForegroundColor Red
    exit 1
}
```

**Uso:**
```powershell
.\firmar.ps1 -ExePath ".\dist\DesktopWhisperTranscriber.exe" -Thumbprint "A1B2C3D4..."
```

### Opción 2: Integrar en build.py

**Modificación a build.py:**
```python
def sign_executable(exe_path: str, thumbprint: str) -> bool:
    """Firma el ejecutable con el certificado."""
    import subprocess
    
    signtool_paths = [
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.19041.0\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22000.0\x64\signtool.exe",
        r"C:\Program Files (x86)\Windows Kits\10\bin\10.0.22621.0\x64\signtool.exe",
    ]
    
    signtool = None
    for path in signtool_paths:
        if os.path.exists(path):
            signtool = path
            break
    
    if not signtool:
        logger.error("signtool.exe no encontrado. Instala Windows SDK.")
        return False
    
    try:
        result = subprocess.run([
            signtool,
            "sign",
            "/sha1", thumbprint,
            "/tr", "http://timestamp.sectigo.com",
            "/td", "sha256",
            "/fd", "sha256",
            "/a",
            exe_path
        ], capture_output=True, text=True, check=True)
        
        logger.info(f"✅ Ejecutable firmado exitosamente: {exe_path}")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Error firmando ejecutable: {e.stderr}")
        return False

# En la función main() de build.py, agregar:
if args.sign and args.thumbprint:
    sign_executable(str(exe_path), args.thumbprint)
```

**Uso del build mejorado:**
```bash
python build.py --sign --thumbprint A1B2C3D4E5F6...
```

### Opción 3: GitHub Actions (Automatizado)

**Workflow con firma:**
```yaml
# .github/workflows/build-and-sign.yml
name: Build and Sign

on:
  push:
    tags:
      - 'v*'

jobs:
  build-and-sign:
    runs-on: windows-latest
    
    steps:
    - uses: actions/checkout@v4
    
    # ... pasos de build ...
    
    - name: Sign executable
      env:
        CERTIFICATE_THUMBPRINT: ${{ secrets.CERTIFICATE_THUMBPRINT }}
      run: |
        signtool sign /sha1 %CERTIFICATE_THUMBPRINT% `
          /tr http://timestamp.sectigo.com `
          /td sha256 /fd sha256 `
          "dist\DesktopWhisperTranscriber.exe"
```

**Nota:** Para GitHub Actions necesitarás:
- Instalar el certificado en un runner auto-hospedado, O
- Usar Azure Key Vault o similar para almacenamiento seguro del certificado

## ✅ Verificación de la Firma

### Método 1: Windows Explorer
1. Click derecho en el ejecutable
2. Propiedades → Firma digital
3. Deberías ver el nombre de tu empresa

### Método 2: PowerShell
```powershell
Get-AuthenticodeSignature "DesktopWhisperTranscriber.exe"
```

Salida esperada:
```
SignerCertificate                         Status
-----------------                         ------
A1B2C3D4E5F6...                           Valid
```

### Método 3: signtool.exe
```powershell
signtool verify /pa DesktopWhisperTranscriber.exe
```

Salida esperada:
```
Successfully verified: DesktopWhisperTranscriber.exe
```

### Método 4: Online (VirusTotal)
1. Sube tu ejecutable a https://www.virustotal.com
2. Debería mostrar la firma válida en la sección "File Details"

## 💰 Consideraciones de Costo

### Presupuesto Anual

**Opción Económica (Sectigo OV):**
- Certificado: ~$200/año
- Hardware token (opcional): ~$50 (único)
- **Total primer año**: ~$250
- **Total años siguientes**: ~$200/año

**Opción Premium (DigiCert EV):**
- Certificado: ~$700/año
- Hardware token incluido
- **Total**: ~$700/año

### Retorno de Inversión (ROI)

**Sin firma:**
- Usuarios ven advertencia de SmartScreen
- Posible abandono de instalación: 30-50%

**Con firma:**
- Sin advertencias
- Instalación fluida
- Mayor confianza = más usuarios

**Para una app con 1000 descargas/año:**
- Costo por instalación completada: $0.20-0.70
- Incremento esperado en instalaciones: 20-40%
- **ROI positivo** con unos pocos usuarios adicionales

## 🆓 Alternativas Gratuitas

### 1. Microsoft Store
- **Costo**: $19 USD (cuenta de desarrollador, único)
- Las apps de la tienda ya están firmadas por Microsoft
- Requiere empaquetar como MSIX
- Proceso de aprobación de Microsoft

### 2. Windows Package Manager (winget)
- **Costo**: Gratis
- Distribución a través de repositorio comunitario
- No elimina SmartScreen, pero facilita instalación
- Requiere manifest YAML

### 3. Chocolatey
- **Costo**: Gratis (repositorio comunitario)
- Similar a winget
- No elimina advertencias de SmartScreen

### 4. Esperar Reputación Orgánica (SmartScreen)
- **Costo**: Gratis, pero lleva tiempo
- Windows SmartScreen eventualmente reconoce la app
- Puede tomar semanas/meses y miles de descargas
- Riesgo: sigue mostrando advertencias inicialmente

## 📋 Checklist Pre-Implementación

- [ ] Presupuesto aprobado ($200-700/año)
- [ ] Decisión OV vs EV tomada
- [ ] Proveedor seleccionado
- [ ] Documentos de validación listos
- [ ] Windows SDK instalado (para signtool)
- [ ] Script de build actualizado
- [ ] Backup de certificado y contraseña
- [ ] Política de renovación establecida

## 🔒 Mejores Prácticas

### Seguridad del Certificado
1. **Nunca compartas** el archivo PFX o la contraseña
2. **Backup seguro** del certificado (cifrado)
3. **Usa hardware token** si es posible (más seguro)
4. **Renueva antes** de la expiración (30 días antes)
5. **Timestamp** todas las firmas (para validez post-expiración)

### Gestión
1. **Documenta** el thumbprint y URL del timestamp
2. **Automatiza** el proceso de firma en CI/CD
3. **Verifica** siempre la firma después del build
4. **Monitorea** la reputación de la app en SmartScreen

## 📞 Soporte y Recursos

### Documentación Oficial
- Microsoft: https://docs.microsoft.com/en-us/windows-hardware/drivers/install/get-a-code-signing-certificate
- DigiCert: https://www.digicert.com/code-signing/
- Sectigo: https://sectigo.com/resource-library/code-signing-certificates

### Comunidad
- Stack Overflow: "code-signing" + "signtool"
- GitHub Issues de este proyecto

## 🎓 Conclusión

La firma de código es una **inversión valiosa** que:
- ✅ Elimina fricción en la instalación
- ✅ Aumenta la confianza del usuario
- ✅ Protege tu marca y reputación
- ✅ Cuesta relativamente poco (~$200-700/año)

**Recomendación**: Empieza con un certificado **OV de Sectigo** (~$200/año) y actualiza a **EV** cuando el proyecto crezca.

---

## 📝 Notas de Implementación

**Estado actual de DesktopWhisperTranscriber:**
- ✅ Sistema de verificación de integridad implementado (FASE 2)
- ✅ Build script con generación de hashes
- ✅ Documentación de verificación de integridad
- ⏳ **Firma de código**: Requiere compra de certificado

**Próximos pasos para implementar firma:**
1. Adquirir certificado OV de Sectigo o similar
2. Instalar Windows SDK (para signtool.exe)
3. Modificar build.py para incluir firma automática
4. Actualizar GitHub Actions (opcional, requiere certificado en cloud)
5. Documentar el thumbprint en README

---

**¿Preguntas sobre la implementación de firma de código?**
Abre un issue en GitHub con el tag "code-signing".
