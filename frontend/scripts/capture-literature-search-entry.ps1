param(
  [string]$BaseUrl = 'http://127.0.0.1:5173',
  [string]$EdgePath = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
)

$ErrorActionPreference = 'Stop'
$outputDirectory = 'D:\AI_project\rag_medicine\docs\frontend-rebuild\screenshots\literature-search-entry'
$referencePath = 'C:\Users\ADMIN\Desktop\rag医学检索\rag医学检索1.2\前端设计1.1\预览图\文献检索\检索中心\检索中心询问图.png'
New-Item -ItemType Directory -Force -Path $outputDirectory | Out-Null

if (-not (Test-Path -LiteralPath $EdgePath)) { throw "Edge not found: $EdgePath" }
foreach ($viewport in @('1536x1024', '1440x900', '1280x800', '1024x768', '768x1024', '390x844')) {
  $imagePath = Join-Path $outputDirectory "entry-$viewport.png"
  $arguments = @('--headless=new', '--disable-gpu', '--force-device-scale-factor=1', '--hide-scrollbars', '--run-all-compositor-stages-before-draw', '--virtual-time-budget=5000', "--window-size=$viewport", "--screenshot=$imagePath", "$BaseUrl/literature-search")
  $edge = Start-Process -FilePath $EdgePath -ArgumentList $arguments -WindowStyle Hidden -PassThru -Wait
  if ($edge.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $imagePath)) { throw "Screenshot failed for $viewport" }
}

Add-Type -AssemblyName System.Drawing
$reference = [System.Drawing.Bitmap]::new($referencePath)
$actual = [System.Drawing.Bitmap]::new((Join-Path $outputDirectory 'entry-1536x1024.png'))
if ($reference.Size -ne $actual.Size) { throw '1536 baseline dimensions do not match the reference.' }
$overlay = [System.Drawing.Bitmap]::new($reference.Width, $reference.Height)
$diff = [System.Drawing.Bitmap]::new($reference.Width, $reference.Height)
$graphics = [System.Drawing.Graphics]::FromImage($overlay)
$graphics.DrawImage($reference, 0, 0)
$attributes = [System.Drawing.Imaging.ImageAttributes]::new()
$matrix = [System.Drawing.Imaging.ColorMatrix]::new()
$matrix.Matrix33 = 0.5
$attributes.SetColorMatrix($matrix)
$graphics.DrawImage($actual, [System.Drawing.Rectangle]::new(0, 0, $actual.Width, $actual.Height), 0, 0, $actual.Width, $actual.Height, [System.Drawing.GraphicsUnit]::Pixel, $attributes)
$graphics.Dispose(); $attributes.Dispose()
$differentPixels = 0L
for ($y = 0; $y -lt $reference.Height; $y++) { for ($x = 0; $x -lt $reference.Width; $x++) { $a = $reference.GetPixel($x, $y); $b = $actual.GetPixel($x, $y); $delta = [math]::Abs($a.R-$b.R)+[math]::Abs($a.G-$b.G)+[math]::Abs($a.B-$b.B); if ($delta -gt 24) { $differentPixels++; $diff.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, [math]::Min(255,$delta), 0, 0)) } else { $diff.SetPixel($x, $y, [System.Drawing.Color]::FromArgb(255, 255,255,255)) } } }
$overlay.Save((Join-Path $outputDirectory 'entry-1536x1024-overlay.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$diff.Save((Join-Path $outputDirectory 'entry-1536x1024-diff.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$report = @{ reference = '1536x1024'; implementation = 'entry-1536x1024.png'; differentPixels = $differentPixels; viewportChecks = @('1536x1024','1440x900','1280x800','1024x768','768x1024','390x844'); status = 'visual artifacts generated; DOM geometry requires browser-protocol measurement' } | ConvertTo-Json
$report | Set-Content -Encoding utf8 (Join-Path $outputDirectory 'geometry-report.json')
$reference.Dispose(); $actual.Dispose(); $overlay.Dispose(); $diff.Dispose()
