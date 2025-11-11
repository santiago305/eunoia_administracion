# scripts/open_chrome_debug.ps1
# Abre Google Chrome con depuración remota y un perfil aislado.
# Permite pasar una URL (param -Url) o tomarla de .env (LOGIN_URL).
# Guarda PID/PUERTO/PERFIL para cierre posterior con close_chrome_debug.ps1.

param(
  [string]$Url        = "",
  [string]$EnvPath    = "..\.env",
  [int]   $Port,
  [string]$UserData   = "",
  [string]$ChromePath = ""
)

$ErrorActionPreference = "Stop"

# Defaults
if (-not $Port)     { $Port = 9227 }
if (-not $UserData) { $UserData = "C:\chrome-fuvex" }

$projRoot = Split-Path -Parent $PSScriptRoot
$envFile  = Join-Path $projRoot $EnvPath
$hasEnv   = Test-Path -LiteralPath $envFile

# Leer .env para CHROME_PATH, CHROME_USER_DATA_DIR, CDP_ENDPOINT, LOGIN_URL
if ($hasEnv) {
  foreach ($line in Get-Content -LiteralPath $envFile -ErrorAction SilentlyContinue) {
    if ($line -match '^\s*#') { continue }
    if ($line -match '^\s*$') { continue }

    if (-not $ChromePath -and $line -match '^\s*CHROME_PATH\s*=\s*(.+)$') {
      $ChromePath = $Matches[1].Trim()
    }
    if (($UserData -eq '' -or $UserData -eq 'C:\chrome-fuvex-profile') -and $line -match '^\s*CHROME_USER_DATA_DIR\s*=\s*(.+)$') {
      $UserData = $Matches[1].Trim()
    }
    if (-not $Url -and $line -match '^\s*LOGIN_URL\s*=\s*(.+)$') {
      $Url = $Matches[1].Trim()
    }
    if (-not $Port -or $Port -eq 9222) {
      if ($line -match '^\s*CDP_ENDPOINT\s*=\s*(.+)$') {
        $ep = $Matches[1].Trim()
        $m = [regex]::Match($ep, ':(\d+)\s*$')
        if ($m.Success) { $Port = [int]$m.Groups[1].Value }
      }
    }
  }
}

# Si no hay URL, usar la predeterminada sin pedir interacción
if (-not $Url) {
  $Url = "https://fuvexbn.a365.com.pe:7443/index.php"
  Write-Host ("No se proporcionó LOGIN_URL ni parámetro -Url. Usando URL predeterminada: {0}" -f $Url) -ForegroundColor Yellow
}

# Resolver Chrome
if (-not $ChromePath) {
  $cands = @(
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "$env:ProgramFiles(x86)\Google\Chrome\Application\chrome.exe"
  )
  foreach ($c in $cands) { if (Test-Path $c) { $ChromePath = $c; break } }
}
if (-not $ChromePath) {
  Write-Host "No se encontró Google Chrome. Define CHROME_PATH en .env o edita este script." -ForegroundColor Yellow
  exit 1
}

# Crear perfil si no existe
if (-not (Test-Path -LiteralPath $UserData)) {
  New-Item -ItemType Directory -Force -Path $UserData | Out-Null
}

# Lanzar Chrome
try {
  $proc = Start-Process -FilePath $ChromePath -ArgumentList @(
    "--remote-debugging-port=$Port",
    "--user-data-dir=$UserData",
    "--start-maximized",
    $Url
  ) -PassThru
} catch {
  Write-Host ("Error al lanzar Chrome: {0}" -f $_.Exception.Message) -ForegroundColor Red
  exit 1
}

# Guardar metadatos para cierre posterior
$metaDir  = $PSScriptRoot
$pidFile  = Join-Path $metaDir "chrome_cdp.pid"
$portFile = Join-Path $metaDir "chrome_cdp_port.txt"
$profFile = Join-Path $metaDir "chrome_cdp_profile.txt"

$proc.Id  | Out-File -Encoding ascii -Force $pidFile
$Port     | Out-File -Encoding ascii -Force $portFile
$UserData | Out-File -Encoding ascii -Force $profFile

Write-Host ("`n>>> Chrome abierto (PID {0}) en puerto {1}, perfil '{2}'." -f $proc.Id, $Port, $UserData)
Write-Host (">>> Se abrió: {0}" -f $Url)
Write-Host ">>> Ingresa tu usuario/contraseña y resuelve el CAPTCHA normalmente."
exit 0
