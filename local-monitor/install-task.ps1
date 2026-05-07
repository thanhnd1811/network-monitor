<#
    install-task.ps1

    Cài đặt Windows Scheduled Task để tự động chạy ftu-netmon-probe.exe
    mỗi 1 phút, kể cả khi không có ai đăng nhập.

    Chạy 1 lần với quyền Administrator:
        Click chuột phải -> "Run with PowerShell as Administrator"
    HOẶC trong PowerShell admin:
        .\install-task.ps1
#>

[CmdletBinding()]
param(
    [int] $IntervalMinutes = 1,
    [string] $TaskName = "FTU NetMon Probe"
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$exePath = Join-Path $here "ftu-netmon-probe.exe"
$configPath = Join-Path $here "config.json"

Write-Host ""
Write-Host "==> FTU NetMon - Cai dat Scheduled Task" -ForegroundColor Cyan
Write-Host ""

# Check files exist
if (-not (Test-Path $exePath)) {
    Write-Host "LOI: khong tim thay $exePath" -ForegroundColor Red
    Write-Host "       Anh phai dat install-task.ps1 cung thu muc voi ftu-netmon-probe.exe" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $configPath)) {
    Write-Host "LOI: khong tim thay $configPath" -ForegroundColor Red
    Write-Host ""
    Write-Host "Cach lam:" -ForegroundColor Yellow
    Write-Host "  1. Copy config.json.example thanh config.json" -ForegroundColor Gray
    Write-Host "  2. Mo config.json bang Notepad, sua dong github_token" -ForegroundColor Gray
    Write-Host "  3. Chay lai script nay" -ForegroundColor Gray
    exit 1
}

# Check admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "LOI: Script can quyen Administrator." -ForegroundColor Red
    Write-Host "     Click chuot phai vao file install-task.ps1 -> chon 'Run with PowerShell as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Validate config has token
try {
    $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($cfg.github_token -eq "PASTE-PERSONAL-ACCESS-TOKEN-HERE" -or [string]::IsNullOrWhiteSpace($cfg.github_token)) {
        Write-Host "LOI: github_token chua duoc dien trong config.json" -ForegroundColor Red
        Write-Host "     Mo config.json bang Notepad, dien Personal Access Token vao." -ForegroundColor Yellow
        exit 1
    }
} catch {
    Write-Host "LOI: config.json bi loi cu phap JSON. $_" -ForegroundColor Red
    exit 1
}

Write-Host "[1/4] Test chay probe 1 lan de kiem tra ket noi..." -ForegroundColor Yellow
$proc = Start-Process -FilePath $exePath -WorkingDirectory $here -PassThru -Wait -NoNewWindow
if ($proc.ExitCode -ne 0) {
    Write-Host "LOI: probe chay loi (exit code $($proc.ExitCode)). Xem probe.log de biet chi tiet." -ForegroundColor Red
    Write-Host "     Khong cai task. Sua loi roi chay lai." -ForegroundColor Red
    exit 1
}
Write-Host "    Test OK!" -ForegroundColor Green
Write-Host ""

Write-Host "[2/4] Xoa task cu (neu co)..." -ForegroundColor Yellow
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "[3/4] Tao Scheduled Task moi (chay moi $IntervalMinutes phut)..." -ForegroundColor Yellow
$action = New-ScheduledTaskAction -Execute $exePath -WorkingDirectory $here
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest -LogonType ServiceAccount
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description "Ping cac duong mang truong DH Ngoai thuong va day ket qua len GitHub. Run as SYSTEM." `
    | Out-Null

Write-Host "[4/4] Khoi chay task lan dau..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $TaskName

Write-Host ""
Write-Host "XONG!" -ForegroundColor Green
Write-Host ""
Write-Host "Task da duoc cai:" -ForegroundColor Cyan
Write-Host "  Ten task     : $TaskName" -ForegroundColor White
Write-Host "  Chay moi     : $IntervalMinutes phut" -ForegroundColor White
Write-Host "  Chay duoi    : SYSTEM (khong can dang nhap)" -ForegroundColor White
Write-Host "  Log file     : $here\probe.log" -ForegroundColor White
Write-Host ""
Write-Host "Mo Task Scheduler de xem/dieu chinh:" -ForegroundColor Cyan
Write-Host "  Win+R -> taskschd.msc -> Task Scheduler Library -> '$TaskName'" -ForegroundColor Gray
Write-Host ""
Write-Host "Go bo task khi can:" -ForegroundColor Cyan
Write-Host "  Unregister-ScheduledTask -TaskName '$TaskName' -Confirm" -ForegroundColor Gray
Write-Host ""
