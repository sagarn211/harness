$ErrorActionPreference = 'Stop'
$env:OLLAMA_HOST = if ($env:OLLAMA_HOST) { $env:OLLAMA_HOST } else { 'http://localhost:11434' }
try { Invoke-WebRequest -UseBasicParsing "$env:OLLAMA_HOST/api/tags" -TimeoutSec 2 | Out-Null } catch { Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden }
Write-Host 'Server running at http://localhost:8000'
& .\.venv\Scripts\python.exe -m uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
