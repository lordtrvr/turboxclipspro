$root    = "C:\Users\potii\Desktop\TurboxWeb"
$python  = "C:\Users\potii\AppData\Local\Programs\Python\Python311\python.exe"
$cf      = "C:\Program Files (x86)\cloudflared\cloudflared.exe"
$ts      = "C:\Program Files\Tailscale\tailscale.exe"
$logOut  = Join-Path $root "cloudflared.out.log"
$logErr  = Join-Path $root "cloudflared.err.log"
$urlFile = Join-Path $root "URL_DEL_PANEL.txt"

function Get-TsUrl {
  if (-not (Test-Path $ts)) { return $null }
  $txt = (& $ts serve status 2>&1 | Out-String)
  $m = [regex]::Match($txt, 'https://[a-z0-9-]+(?:\.[a-z0-9-]+)+\.ts\.net')
  if ($m.Success) { return $m.Value + "/admin" }
  return $null
}

# 1) Asegurar que el servidor este corriendo
$uv = Get-CimInstance Win32_Process -Filter "Name like '%python%'" |
      Where-Object { $_.CommandLine -like '*uvicorn backend.main:app*' }
if (-not $uv) {
  Start-Process -FilePath $python `
    -ArgumentList "-m uvicorn backend.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory $root -WindowStyle Minimized
}
Start-Sleep -Seconds 2

$url = $null

# 2) Intentar Tailscale (link fijo, solo tus dispositivos)
if (Test-Path $ts) {
  $st = (& $ts status 2>&1 | Out-String)
  if ($st -notmatch 'Logged out|NeedsLogin') {
    & $ts serve --bg --yes 8000 2>&1 | Out-Null
    Start-Sleep -Seconds 3
    $url = Get-TsUrl
    if ($url) {
      # Ya no necesitamos el tunel publico
      Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" |
        ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
    }
  }
}

# 3) Si no hay Tailscale, usar Cloudflare Tunnel como respaldo
if (-not $url -and (Test-Path $cf)) {
  Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" |
    Where-Object { $_.CommandLine -like '*--url http://127.0.0.1:8000*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Remove-Item $logOut, $logErr -ErrorAction SilentlyContinue
  Start-Process -FilePath $cf `
    -ArgumentList "tunnel --url http://127.0.0.1:8000" `
    -WorkingDirectory $root -WindowStyle Minimized `
    -RedirectStandardOutput $logOut -RedirectStandardError $logErr
  for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    $txt = ((Get-Content $logOut, $logErr -Raw -ErrorAction SilentlyContinue) -join "`n")
    $m = [regex]::Match($txt, 'https://[a-z0-9-]+\.trycloudflare\.com')
    if ($m.Success) { $url = $m.Value + "/admin"; break }
  }
}

# 4) Mostrar el link
if ($url) {
  $modo = if ($url -like '*.ts.net/*') { "TAILSCALE (privado, link fijo)" } else { "CLOUDFLARE (link temporal)" }
  "MODO: $modo`n`nURL DEL PANEL`n$url`n`nContrasena: la configurada en .env (ADMIN_PASSWORD)`n" |
    Set-Content $urlFile -Encoding UTF8
  Start-Process notepad $urlFile
  Write-Host "LISTO ($modo): $url"
} else {
  Write-Host "No se pudo obtener la URL. Inicia sesion en Tailscale y vuelve a ejecutar."
}
