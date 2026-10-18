# Genera el paquete para Elastic Beanstalk desde la carpeta de trabajo
# (incluye cambios sin commit) escribiendo la version en el archivo VERSION.
# Uso: .\scripts\build-zip.ps1 -Version 1.0.1
param(
    [Parameter(Mandatory = $true)][string]$Version,
    [string]$OutDir
)

$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if (-not $OutDir) { $OutDir = Join-Path $root "dist" }
Set-Content -Path (Join-Path $root "VERSION") -Value $Version -Encoding ascii -NoNewline

New-Item -ItemType Directory -Force $OutDir | Out-Null
$zipPath = Join-Path (Resolve-Path $OutDir).Path "blacklist-v$Version.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

# Archivos versionados + nuevos no ignorados, sin entregas/, dist/ ni postman/.
$files = git -C $root ls-files --cached --others --exclude-standard |
    Where-Object { $_ -notmatch '^(entregas|dist|postman)/' } | Sort-Object -Unique
if ($files -notcontains "VERSION") { $files += "VERSION" }

Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::Open($zipPath, 'Create')
try {
    foreach ($f in $files) {
        $full = Join-Path $root $f
        if (Test-Path $full -PathType Leaf) {
            # Rutas con "/" para que el unzip de Amazon Linux las respete.
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile($zip, $full, $f.Replace('\', '/')) | Out-Null
        }
    }
} finally { $zip.Dispose() }
Write-Host "Paquete: $zipPath ($($files.Count) archivos)"
