; Script de Inno Setup para DesktopWhisperTranscriber
; ==================================================

; --- Definiciones de Macros ---
; Estas macros facilitan la actualización de la información en un solo lugar.
#define MyAppName "DesktopWhisperTranscriber"
#define MyAppVersion "0.1.0-beta" ; Actualiza esto para futuras versiones
#define MyAppPublisher "Mi Transcriptor Web" ; Tu nombre o el de tu proyecto
#define MyAppExeName "DesktopWhisperTranscriber.exe" ; El nombre de tu ejecutable principal
#define MyOutputBaseFilename "DesktopWhisperTranscriber_v0.1.0_beta_setup" ; Nombre del archivo de instalación
; #define MyAppURL "https://tu-sitio-web.com" ; Descomenta y edita si tienes un sitio web
; #define MySupportURL "https://tu-sitio-web.com/soporte" ; Descomenta y edita para URL de soporte
; #define MyUpdatesURL "https://tu-sitio-web.com/actualizaciones" ; Descomenta y edita para URL de actualizaciones

[Setup]
; NOTA: El AppId identifica de forma única tu aplicación.
; Si recompilas con un AppId diferente, se tratará como una aplicación diferente.
; {{AUTO}} genera un GUID único la primera vez. Mantenlo si no tienes una razón para cambiarlo.
AppId={{AUTO}} 
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
; Descomenta las siguientes líneas si definiste las macros correspondientes arriba
; AppPublisherURL={#MyAppURL}
; AppSupportURL={#MySupportURL}
; AppUpdatesURL={#MyUpdatesURL}
DefaultDirName={autopf}\{#MyAppName} ; Directorio de instalación por defecto (ej. C:\Program Files (x86)\DesktopWhisperTranscriber)
DefaultGroupName={#MyAppName}      ; Nombre de la carpeta en el Menú Inicio
OutputBaseFilename={#MyOutputBaseFilename}
Compression=lzma2
        ; Mejor compresión
SolidCompression=yes
WizardStyle=modern                
 ; Estilo moderno del asistente de instalación
PrivilegesRequired=admin          
                                  ; Requiere privilegios de administrador para instalar en Program Files.
                                   ; Usa 'lowest' si quieres permitir instalación en carpetas de usuario sin admin,
                                   ; pero entonces cambia DefaultDirName a algo como {userappdata}\{#MyAppName}

[Languages]
; Incluye los idiomas que quieres que soporte tu instalador.
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
; Define tareas opcionales que el usuario puede seleccionar durante la instalación.
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
; Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1 ; Para versiones antiguas de Windows

[Files]
; --- Aplicación Principal ---
; Asegúrate de que esta ruta 'Source' sea correcta relativa a la ubicación de este script .iss
; Asume que el script .iss está en la raíz de MiTranscriptorWeb, y el .exe en MiTranscriptorWeb/dist/
Source: "dist\DesktopWhisperTranscriber.exe"; DestDir: "{app}"; Flags: ignoreversion


; --- FFmpeg Binaries ---
; Asume que tienes una carpeta llamada 'ffmpeg' en la raíz de MiTranscriptorWeb (junto a este .iss)
; y que contiene ffmpeg.exe, ffprobe.exe y todas las DLLs necesarias.
Source: "ffmpeg\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion
; Source: "ffmpeg\*.dll"; DestDir: "{app}"; Flags: ignoreversion ;

; 'recursesubdirs createallsubdirs' por si alguna DLL estuviera en una subcarpeta dentro de 'ffmpeg', aunque no es lo usual para las DLLs de ffmpeg.
; Si todas las DLLs están directamente en 'ffmpeg', 'recursesubdirs createallsubdirs' no es estrictamente necesario para la línea de *.dll.

; --- Otros Assets (Ejemplo: Fuentes) ---
; Si tienes una fuente que debe instalarse con la aplicación y PyInstaller no la empaquetó dentro del .exe
; Por ejemplo, si tu fuente DejaVuSans.ttf está en MiTranscriptorWeb/assets/fonts/
; Source: "assets\fonts\DejaVuSans.ttf"; DestDir: "{app}\assets\fonts"; Flags: ignoreversion fontinstall
; El flag 'fontinstall' es para registrar la fuente en el sistema, pero para fpdf2
; es suficiente con que esté en una ruta accesible por la aplicación.
; Para fpdf2, es mejor que la ruta a la fuente sea relativa a la aplicación,
; por lo que copiarla a un subdirectorio 'assets\fonts' dentro de {app} es una buena práctica.
; Asegúrate de que tu código Python busque la fuente en esta ubicación relativa.
; Si tu PyInstaller ya empaqueta la fuente correctamente, no necesitas esta línea.

; --- Archivo README o de Licencia (Opcional) ---
; Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
; Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Crea iconos en el Menú Inicio y, opcionalmente, en el Escritorio.
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Ejecuta la aplicación después de que la instalación se complete (opcional).
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

; [UninstallDelete]
; Descomenta y modifica si quieres que el desinstalador borre archivos/carpetas específicas
; que tu aplicación podría haber creado (ej. logs, configuraciones de usuario, descargas).
; Type: filesandordirs; Name: "{app}\youtube_downloads" ; Borra la carpeta de descargas de YouTube y su contenido
; Type: files; Name: "{userappdata}\{#MyAppName}\settings.ini" ; Borra un archivo de configuración