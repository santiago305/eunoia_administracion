$metaDir = $PSScriptRoot
$pidFile = Join-Path $metaDir "chrome_cdp.pid"
$portFile = Join-Path $metaDir "chrome_cdp_port.txt"
$profFile = Join-Path $metaDir "chrome_cdp_profile.txt"

$chromePid = $null; $port = $null; $profileDir = $null
if (Test-Path $pidFile)  { $chromePid = Get-Content $pidFile  | Select-Object -First 1 }
if (Test-Path $portFile) { $port = Get-Content $portFile | Select-Object -First 1 }
if (Test-Path $profFile) { $profileDir = Get-Content $profFile | Select-Object -First 1 }

# 1) Intenta matar por PID
if ($chromePid) { try { Stop-Process -Id $chromePid -Force -ErrorAction SilentlyContinue } catch {} }

# 2) Cierra cualquier chrome.exe con ese perfil o puerto en su línea de comandos
try {
  $procs = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'chrome.exe' -and (
      ($profileDir -and $_.CommandLine -like "*$profileDir*") -or
      ($port -and $_.CommandLine -like "*remote-debugging-port=$port*")
    )
  }
  foreach ($p in $procs) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
} catch {}

Remove-Item -Force -ErrorAction SilentlyContinue $pidFile, $portFile, $profFile
Write-Host ">>> Chrome (CDP) cerrado."
exit 0
