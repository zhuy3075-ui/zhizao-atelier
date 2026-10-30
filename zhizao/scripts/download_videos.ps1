# 批量下载视频（配合 scripts/video_links.py 导出的 CSV）
#
#   .\download_videos.ps1 -Csv "links.csv" -Out "D:\视频\某人"
#   .\download_videos.ps1 -Csv "links.csv" -Out ".\videos" -Index "1,3,5-8"
#   .\download_videos.ps1 -Csv "links.csv" -Out ".\videos" -DryRun     # 只看有多少条
#
# 链接带签名、几小时失效。脚本会断点续：已存在且大小正常的跳过，失败会打印真实原因。
param(
    [Parameter(Mandatory = $true)][string]$Csv,
    [string]$Out = ".\videos",
    [string]$Index = "",
    [int]$DelaySec = 1,
    [switch]$DryRun
)

$ErrorActionPreference = "Continue"
if (-not (Test-Path $Csv)) { throw "找不到 CSV：$Csv（先用 scripts/video_links.py --out 导出）" }

$rows = Import-Csv $Csv -Encoding UTF8 | Where-Object { $_.video_url }
if (-not $rows) { throw "CSV 里没有可用的 video_url 列，检查文件是不是 video_links.py 导出的" }

if ($Index) {
    $want = @()
    foreach ($part in $Index.Split(",")) {
        $part = $part.Trim()
        if ($part -match "^(\d+)-(\d+)$") { $want += [int]$Matches[1]..[int]$Matches[2] }
        elseif ($part -match "^\d+$") { $want += [int]$part }
    }
    $picked = @()
    for ($i = 0; $i -lt $rows.Count; $i++) { if ($want -contains ($i + 1)) { $picked += $rows[$i] } }
    $rows = $picked
}

if ($DryRun) {
    "共 $($rows.Count) 条待下载："
    $i = 0
    foreach ($r in $rows) { $i++; "  [{0}] {1}" -f $i, $r.title }
    return
}

New-Item -ItemType Directory -Force -Path $Out | Out-Null
"共 $($rows.Count) 条，输出到 $((Resolve-Path $Out).Path)"
""

$i = 0; $okCount = 0; $failCount = 0; $totalMB = 0; $skipCount = 0
$useCurl = [bool](Get-Command curl.exe -ErrorAction SilentlyContinue)

foreach ($r in $rows) {
    $i++
    $name = ($r.title -replace '[\\/:*?"<>|]', '_')
    $name = $name.Substring(0, [Math]::Min(50, $name.Length))
    $ext = if ($r.video_url -match "\.m4a") { ".m4a" } else { ".mp4" }
    $file = Join-Path $Out ("{0:d2}_{1}{2}" -f $i, $name, $ext)

    if ((Test-Path $file) -and (Get-Item $file).Length -gt 10KB) {
        "  [$i] 已存在，跳过"
        $skipCount++; $totalMB += (Get-Item $file).Length / 1MB
        continue
    }

    Write-Host ("  [{0}] 下载中  {1}" -f $i, $r.title.Substring(0, [Math]::Min(26, $r.title.Length))) -NoNewline
    try {
        if ($useCurl) {
            & curl.exe -sS -L --fail --max-time 1800 -A "Mozilla/5.0" -o "$file" "$($r.video_url)" 2>$null
        } else {
            Invoke-WebRequest -Uri $r.video_url -OutFile $file -TimeoutSec 1800
        }
        if ((Test-Path $file) -and (Get-Item $file).Length -gt 10KB) {
            $mb = [math]::Round((Get-Item $file).Length / 1MB, 1)
            $totalMB += $mb; $okCount++
            Write-Host "  ✓ $mb MB" -ForegroundColor Green
        } else {
            throw "文件没下下来（链接可能已过期）"
        }
    } catch {
        $msg = if ($_.Exception.Message) { $_.Exception.Message } else { "curl 失败" }
        Write-Host "  ✗ $msg" -ForegroundColor Red
        $failCount++
        Remove-Item $file -Force -ErrorAction SilentlyContinue
    }
    Start-Sleep -Seconds $DelaySec
}

""
"成功 $okCount  跳过 $skipCount  失败 $failCount  合计 $([math]::Round($totalMB/1024,2)) GB"
"目录：$((Resolve-Path $Out).Path)"
if ($failCount -gt 0) { "有失败项：先看上面的原因；若是链接过期，重跑 video_links.py 取新链接。" }
