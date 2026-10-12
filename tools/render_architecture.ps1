$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$root = Split-Path $PSScriptRoot -Parent
$scene = Get-Content -LiteralPath (Join-Path $root 'assets\architecture.scene.json') -Raw | ConvertFrom-Json
$bmp = [System.Drawing.Bitmap]::new([int]$scene.width, [int]$scene.height)
$graphics = [System.Drawing.Graphics]::FromImage($bmp)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
$graphics.Clear([System.Drawing.Color]::White)
$font = New-Object System.Drawing.Font('Segoe UI', 10)
$titleFont = New-Object System.Drawing.Font('Segoe UI', 12)
$headingFont = New-Object System.Drawing.Font('Segoe UI', 17)
$black = [System.Drawing.Brushes]::Black
$graphics.DrawString('Construction ZEB workshop | offline-authored architecture illustration', $headingFont, $black, 30, 20)
$palette = @{ blue=@('#0078D4','#CFE4FA'); purple=@('#5C2D91','#E8DAEF'); green=@('#107C10','#DFF6DD'); orange=@('#F7630C','#FFF4CE'); future=@('#64748B','#F3F2F1'); container=@('#0078D4','') }
foreach ($box in $scene.boxes) {
    $color = $palette[$box[6]]
    $pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml($color[0]), 2)
    if ($box[6] -eq 'future') { $pen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash }
    if ($color[1]) {
        $brush = New-Object System.Drawing.SolidBrush([System.Drawing.ColorTranslator]::FromHtml($color[1]))
        $graphics.FillRectangle($brush, [single]$box[0], [single]$box[1], [single]$box[2], [single]$box[3])
        $brush.Dispose()
    }
    $graphics.DrawRectangle($pen, [single]$box[0], [single]$box[1], [single]$box[2], [single]$box[3])
    $graphics.DrawString($box[4], $titleFont, $black, [single]($box[0]+14), [single]($box[1]+12))
    $graphics.DrawString($box[5], $font, $black, [single]($box[0]+14), [single]($box[1]+43))
    $pen.Dispose()
}
foreach ($a in $scene.arrows) {
    $pen = New-Object System.Drawing.Pen([System.Drawing.ColorTranslator]::FromHtml('#0078D4'), 2)
    $pen.CustomEndCap = New-Object System.Drawing.Drawing2D.AdjustableArrowCap(4, 5)
    if ($a[4]) { $pen.DashStyle = [System.Drawing.Drawing2D.DashStyle]::Dash }
    $graphics.DrawLine($pen, [single]$a[0], [single]$a[1], [single]$a[2], [single]$a[3])
    $pen.Dispose()
}
$graphics.DrawString("Solid: core flow. Dashed: optional / future. Diagram is NOT a live screenshot.`nCapacity remains paused. No cloud deployment, agent run or rehearsal has been performed.", $titleFont, $black, 30, 950)
$bmp.Save((Join-Path $root 'assets\architecture.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$font.Dispose(); $titleFont.Dispose(); $headingFont.Dispose(); $graphics.Dispose(); $bmp.Dispose()
Write-Output 'Rendered architecture PNG offline (not a screenshot).'
