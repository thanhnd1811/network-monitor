<#
    push-to-github.ps1

    Một-bấm script để đưa toàn bộ project lên GitHub.
    Anh chỉ cần:
      1. Tạo 1 repo TRỐNG trên github.com (hướng dẫn trong README.md)
      2. Mở PowerShell tại thư mục này, chạy:
            .\push-to-github.ps1 -GithubUser "TEN-CUA-ANH" -RepoName "ten-repo"

    Script tự làm: git init, add, commit, đẩy lên repo, kích hoạt branch main.
#>
param(
    [Parameter(Mandatory=$true)] [string] $GithubUser,
    [Parameter(Mandatory=$true)] [string] $RepoName
)

$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host ""
Write-Host "==> Project: $here" -ForegroundColor Cyan
Write-Host "==> Sẽ đẩy lên: https://github.com/$GithubUser/$RepoName" -ForegroundColor Cyan
Write-Host ""

# 1. Init git nếu chưa có
if (-not (Test-Path ".git")) {
    Write-Host "[1/5] git init..." -ForegroundColor Yellow
    git init -b main
} else {
    Write-Host "[1/5] git repo đã có, bỏ qua init." -ForegroundColor Yellow
    git checkout -B main
}

# 2. Cấu hình remote
Write-Host "[2/5] Cấu hình remote origin..." -ForegroundColor Yellow
$remoteUrl = "https://github.com/$GithubUser/$RepoName.git"
$existing = git remote get-url origin 2>$null
if ($LASTEXITCODE -eq 0) {
    git remote set-url origin $remoteUrl
} else {
    git remote add origin $remoteUrl
}

# 3. Add + commit
Write-Host "[3/5] Stage + commit toàn bộ file..." -ForegroundColor Yellow
git add -A
$staged = git diff --cached --name-only
if (-not $staged) {
    Write-Host "    (không có thay đổi mới để commit)" -ForegroundColor DarkGray
} else {
    git commit -m "Initial commit: network monitor + web dashboard + Android APK build"
}

# 4. Push
Write-Host "[4/5] Push lên GitHub (anh có thể được hỏi đăng nhập GitHub)..." -ForegroundColor Yellow
git push -u origin main

# 5. Done
Write-Host ""
Write-Host "[5/5] XONG!" -ForegroundColor Green
Write-Host ""
Write-Host "Bước tiếp theo (mở trình duyệt vào):" -ForegroundColor Cyan
Write-Host ""
Write-Host "  1. Bật GitHub Pages:" -ForegroundColor White
Write-Host "     https://github.com/$GithubUser/$RepoName/settings/pages" -ForegroundColor Yellow
Write-Host "     -> Build and deployment -> Source: chon 'GitHub Actions'" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Kich hoat workflow lan dau (cron chua chay ngay):" -ForegroundColor White
Write-Host "     https://github.com/$GithubUser/$RepoName/actions/workflows/monitor.yml" -ForegroundColor Yellow
Write-Host "     -> bam 'Run workflow' -> 'Run workflow'" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Sau khi build APK xong (~3-5 phut), tai APK ve dien thoai:" -ForegroundColor White
Write-Host "     https://github.com/$GithubUser/$RepoName/releases/latest" -ForegroundColor Yellow
Write-Host ""
Write-Host "  4. Mo trang web dashboard tren may tinh:" -ForegroundColor White
Write-Host "     https://$($GithubUser.ToLower()).github.io/$RepoName/" -ForegroundColor Yellow
Write-Host ""
