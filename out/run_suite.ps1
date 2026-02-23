$repo = "C:\Users\Conor O'Brien\Documents\GitHub\AFM-Data-Management"
$inputRoot = "C:\Users\Conor O'Brien\Dropbox\03_AML\03 References and Materials\RAW DATA Files\AFM Scans\Particle Density for Fracture Surfaces Verification\102025-CRO\DATA\PEGDA1TPO00SiNP_Sam01_S1"
$mainOutDir = "C:\Users\Conor O'Brien\Dropbox\03_AML\04 Workbench"
$runStamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outBase = Join-Path $mainOutDir ("AFM_Modulus_Tests_" + $runStamp)
$configDir = "configs/TEST configs/Example configs"

Set-Location $repo
New-Item -ItemType Directory -Force -Path $outBase | Out-Null
$log = Join-Path $outBase "run_suite.log"
Add-Content -Path $log -Value "start $(Get-Date)"

$cfgNames = @(
  "config.modulus_gwy_ops_py_stats.yaml",
  "config.modulus_gwy_stats.yaml",
  "config.modulus_raw_minmax.yaml",
  "config.modulus_raw_chauvenet_three_sigma_debug.yaml"
)
$cfgPaths = $cfgNames | ForEach-Object { Join-Path $configDir $_ }
foreach ($cfgPath in $cfgPaths) {
  if (-not (Test-Path $cfgPath)) {
    Add-Content -Path $log -Value "Missing config: $cfgPath"
    continue
  }
  $cfgName = [System.IO.Path]::GetFileNameWithoutExtension($cfgPath)
  $outRoot = Join-Path $outBase $cfgName

  $jobsOut = & py -3 -c "import yaml,sys; cfg=yaml.safe_load(open(sys.argv[1], 'r', encoding='utf-8')) or {}; jobs=cfg.get('jobs') or {}; print('\n'.join(jobs.keys()))" $cfgPath
  if ($LASTEXITCODE -ne 0) {
    Add-Content -Path $log -Value "Failed to parse jobs for $cfgPath"
    continue
  }
  $jobList = $jobsOut -split "`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ }
  if (-not $jobList) {
    Add-Content -Path $log -Value "No jobs in $cfgName, skipping."
    continue
  }

  foreach ($job in $jobList) {
    Add-Content -Path $log -Value "Running $cfgName :: $job"
    & py -3 scripts/run_job.py --config "$cfgPath" --job "$job" --input-root "$inputRoot" --output-root "$outRoot" *>> $log
    if ($LASTEXITCODE -ne 0) {
      Add-Content -Path $log -Value "Job failed: $cfgName :: $job"
      break
    }
  }
}
Add-Content -Path $log -Value "done $(Get-Date)"
