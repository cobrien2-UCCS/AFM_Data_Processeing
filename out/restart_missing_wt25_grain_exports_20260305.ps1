$ErrorActionPreference = "Stop"

$repoRoot = "C:\Users\Conor O'Brien\Documents\GitHub\AFM-Data-Management"
$configPath = "configs\TEST configs\Example configs\config.topo_particle_2jobs_masking.yaml"

$targets = @(
    @{
        Sample = "PEGDA1TPO25SiNP_Sam02_S1"
        InputRoot = "C:\Users\Conor O'Brien\Dropbox\03_AML\03 References and Materials\RAW DATA Files\AFM Scans\Particle Density for Fracture Surfaces Verification\101325-CRO\DATA\PEGDA1TPO25SiNP_Sam02_S1"
        OutputRoot = "C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\run_grains_full_wt25_20260304_145519\PEGDA_SiNP\PEGDA1TPO25SiNP_Sam02_S1"
        Jobs = @(
            "particle_forward_medianbg_mean",
            "particle_forward_medianbg_fixed0",
            "particle_forward_medianbg_p95",
            "particle_forward_medianbg_max_fixed0_p95",
            "particle_forward_flatten_mean"
        )
    },
    @{
        Sample = "PEGDA1TPO25SiNP_Sam03_S2"
        InputRoot = "C:\Users\Conor O'Brien\Dropbox\03_AML\03 References and Materials\RAW DATA Files\AFM Scans\Particle Density for Fracture Surfaces Verification\101725-CRO\DATA\PEGDA1TPO25SiNP_Sam03_S2"
        OutputRoot = "C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\run_grains_full_wt25_20260304_145519\PEGDA_SiNP\PEGDA1TPO25SiNP_Sam03_S2"
        Jobs = @(
            "particle_forward_medianbg_max_fixed0_p95",
            "particle_forward_flatten_mean",
            "particle_forward_flatten_fixed0",
            "particle_forward_flatten_p95",
            "particle_forward_flatten_max_fixed0_p95"
        )
    }
)

Set-Location $repoRoot

function Test-JobComplete {
    param(
        [string]$JobDir
    )

    if (-not (Test-Path $JobDir)) {
        return $false
    }

    $summaryPath = Join-Path $JobDir "summary.csv"
    $manifestPath = Join-Path $JobDir "job_manifest.json"
    $particleFiles = @(Get-ChildItem (Join-Path $JobDir "particles") -Filter "*_particles.csv" -ErrorAction SilentlyContinue)
    $grainFiles = @(Get-ChildItem (Join-Path $JobDir "grains") -Filter "*_grains.csv" -ErrorAction SilentlyContinue)

    return (Test-Path $summaryPath) -and (Test-Path $manifestPath) -and ($particleFiles.Count -gt 0) -and ($grainFiles.Count -gt 0)
}

foreach ($target in $targets) {
    foreach ($job in $target.Jobs) {
        $jobDir = Join-Path $target.OutputRoot $job
        if (Test-JobComplete -JobDir $jobDir) {
            Write-Host "SKIP complete: $($target.Sample) / $job"
            continue
        }

        Write-Host "RUN  missing detailed exports: $($target.Sample) / $job"
        & py -3 scripts/run_job.py `
            --config $configPath `
            --job $job `
            --input-root $target.InputRoot `
            --output-root $target.OutputRoot
    }
}

Write-Host "Done. Missing wt25 detailed-export restart pass finished."
