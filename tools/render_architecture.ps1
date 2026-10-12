param([string]$EdgePath)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$scene = Get-Content -LiteralPath (Join-Path $root 'assets\architecture.scene.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if (-not $EdgePath) {
    $candidates = @(
        "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
        "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
        "$env:LOCALAPPDATA\Microsoft\Edge\Application\msedge.exe"
    )
    $EdgePath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $EdgePath -or -not (Test-Path -LiteralPath $EdgePath)) {
    throw 'Microsoft Edge is required to rasterize the actual SVG, including Korean fonts and official product icons. Supply -EdgePath or open assets\architecture.svg in a browser.'
}
$profile = Join-Path $root ('.architecture-render-' + [guid]::NewGuid().ToString('N'))
$output = Join-Path $root 'assets\architecture.png'
$rendered = $profile + '.png'
$svg = [uri]::new((Join-Path $root 'assets\architecture.svg')).AbsoluteUri
try {
    # An isolated local-file session never reuses the user's Fabric browser.
    $args = @('--headless=new', '--disable-gpu', '--hide-scrollbars',
        '--no-first-run', '--no-default-browser-check', '--disable-extensions',
        '--disable-background-networking', '--disable-component-update',
        "--user-data-dir=`"$profile`"", "--window-size=$($scene.width),$($scene.height)",
        '--force-device-scale-factor=1', '--virtual-time-budget=3000',
        "--screenshot=`"$rendered`"", "`"$svg`"")
    $process = Start-Process -FilePath $EdgePath -ArgumentList $args -PassThru -WindowStyle Hidden
    if (-not $process.WaitForExit(60000)) {
        Stop-Process -Id $process.Id -Force
        throw 'Architecture SVG rendering timed out.'
    }
    if ($process.ExitCode -ne 0) { throw "Edge exited with code $($process.ExitCode)." }
    if (-not (Test-Path -LiteralPath $rendered)) { throw 'Edge did not produce architecture.png.' }
    Add-Type -AssemblyName System.Drawing
    $image = [System.Drawing.Image]::FromFile($rendered)
    try {
        if ($image.Width -ne $scene.width -or $image.Height -ne $scene.height) {
            throw "Unexpected PNG dimensions: $($image.Width) × $($image.Height)."
        }
    } finally { $image.Dispose() }
    Move-Item -LiteralPath $rendered -Destination $output -Force
    Write-Output "Rendered actual SVG → PNG ($($scene.width) × $($scene.height)); all embedded product icons retained."
} finally {
    if (Test-Path -LiteralPath $rendered) { Remove-Item -LiteralPath $rendered -Force }
    if (Test-Path -LiteralPath $profile) {
        Remove-Item -LiteralPath $profile -Recurse -Force
    }
}
