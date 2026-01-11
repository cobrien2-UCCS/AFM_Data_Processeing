param(
  [Parameter(Mandatory = $true)]
  [string]$InputRoot,

  [string]$Config = "",
  [string]$Profile = "",
  [string]$ProcessingMode = "",
  [string]$CsvMode = "",
  [string]$Pattern = "*.tif;*.tiff",

  [string]$OutputDir = "",
  [string]$ManifestPath = "",

  [string]$Python3 = "python",
  [string]$Python2 = "",

  [switch]$Plot,
  [string]$PlottingMode = "",
  [string]$PlotsOut = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $Config) { $Config = Join-Path $repoRoot "config.yaml" }
if (-not $OutputDir) { $OutputDir = Join-Path $repoRoot "out" }
if (-not $ManifestPath) { $ManifestPath = Join-Path $OutputDir "job_manifest.json" }
if (-not $PlotsOut) { $PlotsOut = Join-Path $OutputDir "plots" }

$Config = (Resolve-Path $Config).Path
$InputRoot = (Resolve-Path $InputRoot).Path

if (-not (Test-Path $OutputDir)) { New-Item -ItemType Directory -Path $OutputDir | Out-Null }

if (-not $Python2) {
  if ($env:PYTHON2_EXE) {
    $Python2 = $env:PYTHON2_EXE
  } elseif (Test-Path "C:\\Python27\\python.exe") {
    $Python2 = "C:\\Python27\\python.exe"
  } else {
    throw "Python 2.7 interpreter not found. Pass -Python2 or set PYTHON2_EXE (e.g. C:\\Python27\\python.exe)."
  }
}

if (-not $env:GWY_BIN) {
  $defaultGwy = "C:\\Program Files (x86)\\Gwyddion\\bin"
  if (Test-Path (Join-Path $defaultGwy "gwyddion.exe")) {
    $env:GWY_BIN = $defaultGwy
  }
}

Write-Host "Repo: $repoRoot"
Write-Host "Config: $Config"
Write-Host "Input: $InputRoot"
Write-Host "Out: $OutputDir"
Write-Host "Manifest: $ManifestPath"
Write-Host "Py3: $Python3"
Write-Host "Py2: $Python2"
if ($env:GWY_BIN) { Write-Host "GWY_BIN: $env:GWY_BIN" }

Write-Host "`n[1/4] Check Py3 environment"
& $Python3 (Join-Path $repoRoot "scripts\\check_env.py")
if ($LASTEXITCODE -ne 0) { throw "Py3 environment check failed. Fix missing packages and retry." }

Write-Host "`n[2/4] Generate manifest (Py3)"
$manifestArgs = @(
  (Join-Path $repoRoot "scripts\\make_job_manifest.py"),
  "--config", $Config,
  "--input-root", $InputRoot,
  "--output-dir", $OutputDir,
  "--out", $ManifestPath,
  "--pattern", $Pattern
)
if ($Profile) { $manifestArgs += @("--profile", $Profile) }
if ($ProcessingMode) { $manifestArgs += @("--processing-mode", $ProcessingMode) }
if ($CsvMode) { $manifestArgs += @("--csv-mode", $CsvMode) }
& $Python3 @manifestArgs
if ($LASTEXITCODE -ne 0) { throw "Manifest generation failed." }

Write-Host "`n[3/4] Check pygwy environment (Py2)"
& $Python2 (Join-Path $repoRoot "scripts\\check_env.py") --require-pygwy
if ($LASTEXITCODE -ne 0) { throw "Py2/pygwy environment check failed. Ensure 32-bit Gwyddion + compatible Python 2.7." }

Write-Host "`n[4/4] Run pygwy processing (Py2)"
& $Python2 (Join-Path $repoRoot "scripts\\run_pygwy_job.py") --manifest $ManifestPath
if ($LASTEXITCODE -ne 0) { throw "pygwy processing failed. See errors above." }

if ($Plot) {
  Write-Host "`n[extra] Plot from CSV (Py3)"
  if (-not (Test-Path $PlotsOut)) { New-Item -ItemType Directory -Path $PlotsOut | Out-Null }

  $manifestObj = Get-Content -Path $ManifestPath | ConvertFrom-Json
  $csvPath = $manifestObj.output_csv
  if (-not $csvPath) { $csvPath = (Join-Path $OutputDir "summary.csv") }

  $plotArgs = @(
    (Join-Path $repoRoot "scripts\\cli_plot.py"),
    "--config", $Config,
    "--csv", $csvPath,
    "--out", $PlotsOut
  )
  if ($PlottingMode) { $plotArgs += @("--plotting-mode", $PlottingMode) }
  elseif ($Profile) { $plotArgs += @("--profile", $Profile) }
  else { $plotArgs += @("--plotting-mode", "heatmap_grid") }

  & $Python3 @plotArgs
  if ($LASTEXITCODE -ne 0) { throw "Plotting failed." }
}

Write-Host "`nDone."
