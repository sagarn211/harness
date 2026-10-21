$ErrorActionPreference = 'Stop'
Start-Process -FilePath 'ngrok' -ArgumentList 'http 11434 --log=stdout' -RedirectStandardOutput "$env:TEMP\ngrok-ollama.log" -WindowStyle Hidden
Start-Process -FilePath 'ngrok' -ArgumentList 'http 8000 --log=stdout' -RedirectStandardOutput "$env:TEMP\ngrok-api.log" -WindowStyle Hidden
Start-Sleep -Seconds 3
$tunnels = (Invoke-RestMethod 'http://127.0.0.1:4040/api/tunnels').tunnels
$ollama = ($tunnels | Where-Object { $_.config.addr -match '11434' } | Select-Object -First 1).public_url
$api = ($tunnels | Where-Object { $_.config.addr -match '8000' } | Select-Object -First 1).public_url
Write-Host "UI URL: $api"
Write-Host "Ollama URL: $ollama"
Write-Host "IMPORTANT: Set OLLAMA_HOST=$ollama in your .env before starting the API."
