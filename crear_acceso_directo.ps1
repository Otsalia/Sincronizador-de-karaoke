# Crea accesos directos con icono (Escritorio y menu Inicio) para abrir el programa
# sin ventana de consola. Se puede ejecutar de nuevo cuando se quiera.
$ErrorActionPreference = "Stop"

$root   = Split-Path -Parent $MyInvocation.MyCommand.Path
$py     = Join-Path $root ".venv\Scripts\pythonw.exe"
$script = Join-Path $root "karaoke_sync.py"
$icon   = Join-Path $root "assets\icon.ico"

if (-not (Test-Path $py)) {
    Write-Host "No se encontro el entorno. Primero ejecuta install.bat"
    exit 1
}

$name  = "Sincronizador de karaoke.lnk"
$shell = New-Object -ComObject WScript.Shell
$dirs  = @(
    [Environment]::GetFolderPath("Desktop"),
    [Environment]::GetFolderPath("Programs")
)

foreach ($dir in $dirs) {
    if (-not $dir) { continue }
    $path = Join-Path $dir $name
    $lnk = $shell.CreateShortcut($path)
    $lnk.TargetPath       = $py
    $lnk.Arguments        = '"' + $script + '"'
    $lnk.WorkingDirectory = $root
    $lnk.IconLocation     = $icon + ",0"
    $lnk.Description      = "Sincronizador de karaoke"
    $lnk.Save()
    Write-Host ("Acceso directo creado: " + $path)
}
