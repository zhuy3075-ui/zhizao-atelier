# lingzao-local 自检：起本地服务，跑全部 13 条命令，报告渲染是否正常。
#   .\smoke.ps1                 # 用 MockBackend
#   .\smoke.ps1 -Port 8790

param(
    [int]$Port = 8787,
    [string]$Client = "C:\Users\Administrator\.agents\skills\lingzao\scripts\lingzao_client.py"
)

$ErrorActionPreference = "Stop"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$env:LINGZAO_BASE_URL = "http://127.0.0.1:$Port"
$env:LINGZAO_API_KEY = "lgz_local"

$proc = Start-Process python -ArgumentList "server.py", "--port", $Port -WorkingDirectory $dir -PassThru -WindowStyle Hidden
Start-Sleep -Seconds 2

$xhs = "https://www.xiaohongshu.com/explore/mock_note_1"
$profile = "https://www.xiaohongshu.com/user/profile/mock_user_1"
$wx = "https://mp.weixin.qq.com/s/mock"
$imgOut = Join-Path $env:TEMP "lz-smoke-img.png"

$cases = @(
    @("doctor", @("doctor")),
    @("search-notes", @("search-notes", "--keyword", "通勤穿搭", "--platform", "xiaohongshu", "--limit", "3")),
    @("search-users", @("search-users", "--keyword", "穿搭", "--platform", "xiaohongshu", "--limit", "3")),
    @("get-note-detail", @("get-note-detail", "--url", $xhs)),
    @("get-note-comments", @("get-note-comments", "--url", $xhs)),
    @("get-user-info", @("get-user-info", "--url", $profile)),
    @("get-user-posted-notes", @("get-user-posted-notes", "--url", $profile)),
    @("analyze-user-profile", @("analyze-user-profile", "--url", $profile)),
    @("get-article-detail", @("get-article-detail", "--url", $wx)),
    @("get-article-stats", @("get-article-stats", "--url", $wx)),
    @("get-related-articles", @("get-related-articles", "--url", $wx)),
    @("extract-video-copy", @("extract-video-copy", "--url", $xhs)),
    @("generate-image", @("generate-image", "--prompt", "smoke test", "--count", "1", "--output", $imgOut))
)

$rows = foreach ($c in $cases) {
    $out = & python $Client @($c[1]) 2>&1 | Out-String
    $code = $LASTEXITCODE
    [pscustomobject]@{
        cmd    = $c[0]
        exit   = $code
        ok     = ($code -eq 0 -and $out -notmatch "Traceback")
        chars  = $out.Length
        head   = (($out -split "`n")[0]).Trim()
    }
}

Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue

$rows | Format-Table -AutoSize
$failed = @($rows | Where-Object { -not $_.ok })
if ($failed.Count -gt 0) {
    Write-Host "$($failed.Count) 个命令失败：$($failed.cmd -join ', ')" -ForegroundColor Red
    exit 1
}
Write-Host "全部 $($rows.Count) 条命令通过" -ForegroundColor Green
