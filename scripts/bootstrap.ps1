param(
  [string]$VenvPath = ".\.venv",
  [string]$Requirements = ".\requirements.txt"
)

$ErrorActionPreference = "Stop"

function Resolve-Python {
  param([string]$VenvPath = ".\.venv")
  $venvPy = Join-Path $VenvPath "Scripts\python.exe"
  if (Test-Path $venvPy) { return $venvPy }
  foreach ($c in @("py","python")) {
    try { & $c -c "import sys;print(sys.version)" 2>$null | Out-Null; if ($LASTEXITCODE -eq 0) { return $c } } catch {}
  }
  throw "No se encontró Python. Instálalo o agrega a PATH."
}

# 1) Crear venv si no existe
if (!(Test-Path $VenvPath)) {
  Write-Host ">> Creando entorno virtual en $VenvPath ..."
  try { & py -3 -m venv $VenvPath } catch { & python -m venv $VenvPath }
}

$PY = Resolve-Python -VenvPath $VenvPath
Write-Host ">> Usando Python: $PY"
& $PY -m pip install --upgrade pip setuptools wheel

# 2) Instalar dependencias
if (Test-Path $Requirements) {
  Write-Host ">> Instalando dependencias desde $Requirements ..."
  & $PY -m pip install -r $Requirements
} else {
  Write-Host ">> Instalando dependencias base ..."
  & $PY -m pip install playwright pandas openpyxl numpy python-dotenv
}

# 3) Instalar navegadores Playwright (inofensivo si ya están)
try { & $PY -m playwright install | Out-Null } catch { Write-Host ">> Advertencia: no se pudieron instalar navegadores de Playwright." -ForegroundColor Yellow }

Write-Host ">> Bootstrap OK."
exit 0
