# MusAgent 本地一键启动（Windows）
# 用法：在 PowerShell 中执行  .\start-local.ps1

$Root = $PSScriptRoot
$Back = Join-Path $Root "back"
$Front = Join-Path $Root "musagent"

if (-not (Test-Path (Join-Path $Back ".env"))) {
    Copy-Item (Join-Path $Back ".env.example") (Join-Path $Back ".env")
    Write-Host "[提示] 已生成 back\.env，请填入 DEEPSEEK_API_KEY 后重新运行（无 Key 也可跑 NLP，LLM 会降级）" -ForegroundColor Yellow
}

Write-Host "安装后端依赖…" -ForegroundColor Cyan
Set-Location $Back
pip install -r requirements.txt -q

Write-Host "安装前端依赖…" -ForegroundColor Cyan
Set-Location $Front
if (-not (Test-Path "node_modules")) { npm install }

Write-Host "启动后端 http://127.0.0.1:8000 …" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Back'; python -m uvicorn main:app --reload --port 8000"

Start-Sleep -Seconds 3

Write-Host "启动前端 http://localhost:5173 …" -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$Front'; npm run dev"

Write-Host ""
Write-Host "已打开两个终端窗口。首次启动会导入诗歌并构建向量索引，约需数分钟。" -ForegroundColor Cyan
Write-Host "浏览器访问: http://localhost:5173" -ForegroundColor Cyan
