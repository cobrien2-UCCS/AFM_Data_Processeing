$ErrorActionPreference = "Stop"

$repo = "C:\Users\Conor O'Brien\Documents\GitHub\AFM-Data-Management"
$py27 = "C:\Python27\python.exe"
$runner = Join-Path $repo "scripts\run_pygwy_job.py"
$wt10Root = "C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\run_grains_full_wt10_20260304_145519"
$wt25Root = "C:\Users\Conor O'Brien\Dropbox\03_AML\00 IN-BOX\AFM Topo Particle processing OUT\run_grains_full_wt25_20260304_145519"
$systemDir = "PEGDA_SiNP"
$primaryJob = "particle_forward_medianbg_mean"
$subsetSamples = @(
    @{ root = $wt10Root; sample = "PEGDA1TPO10SiNP_Sam02_S2" },
    @{ root = $wt25Root; sample = "PEGDA1TPO25SiNP_Sam03_S2" }
)

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$runDir = Join-Path $repo ("out\fast_corrected_topo_" + $stamp)
$outLog = Join-Path $runDir "fast_corrected_topo.out.log"
$errLog = Join-Path $runDir "fast_corrected_topo.err.log"
$doneCsv = Join-Path $runDir "completed_jobs.csv"
$reportRoot = Split-Path $wt10Root -Parent
$reportPath = Join-Path $reportRoot ("topo_particle_report_FAST_CORRECTED_" + $stamp + ".docx")
$chapterPath = Join-Path $repo ("docs\Thesis\Chapter6_Stage1_Results_Feasibility_DRAFT_fast_corrected_" + $stamp + ".docx")

New-Item -ItemType Directory -Force -Path $runDir | Out-Null
"timestamp,job,manifest,exit_code,duration_seconds" | Out-File -FilePath $doneCsv -Encoding utf8

function Write-Log {
    param([string]$Message)
    $line = ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message)
    $line | Tee-Object -FilePath $outLog -Append
}

function Add-Manifest {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$ManifestPath
    )
    if (Test-Path $ManifestPath) {
        $List.Add((Resolve-Path $ManifestPath).Path)
    }
    else {
        ("Missing manifest: {0}" -f $ManifestPath) | Tee-Object -FilePath $errLog -Append
    }
}

Push-Location $repo
try {
    if (-not (Test-Path $py27)) {
        throw "Missing Python 2.7 executable: $py27"
    }
    if (-not (Test-Path $runner)) {
        throw "Missing runner: $runner"
    }

    $manifests = New-Object 'System.Collections.Generic.List[string]'

    foreach ($root in @($wt10Root, $wt25Root)) {
        $sampleBase = Join-Path (Join-Path $root $systemDir) "*"
        Get-ChildItem -Directory $sampleBase | ForEach-Object {
            $manifest = Join-Path $_.FullName $primaryJob
            $manifest = Join-Path $manifest "job_manifest.json"
            Add-Manifest -List $manifests -ManifestPath $manifest
        }
    }

    foreach ($entry in $subsetSamples) {
        $sampleDir = Join-Path (Join-Path (Join-Path $entry.root $systemDir) $entry.sample) "*"
        Get-ChildItem -Directory $sampleDir | ForEach-Object {
            $manifest = Join-Path $_.FullName "job_manifest.json"
            Add-Manifest -List $manifests -ManifestPath $manifest
        }
    }

    $manifestList = $manifests | Sort-Object -Unique
    Write-Log ("Prepared {0} unique manifest reruns." -f $manifestList.Count)
    Write-Log ("Report path: {0}" -f $reportPath)
    Write-Log ("Chapter 6 path: {0}" -f $chapterPath)

    $total = $manifestList.Count
    $index = 0
    foreach ($manifest in $manifestList) {
        $index += 1
        $jobDir = Split-Path $manifest -Parent
        $jobName = Split-Path $jobDir -Leaf
        $sampleName = Split-Path (Split-Path $jobDir -Parent) -Leaf
        $start = Get-Date
        Write-Log ("[{0}/{1}] START {2} :: {3}" -f $index, $total, $sampleName, $jobName)
        & $py27 $runner --manifest $manifest 1>> $outLog 2>> $errLog
        $rc = $LASTEXITCODE
        $dur = [int]((Get-Date) - $start).TotalSeconds
        ('"{0}","{1}","{2}",{3},{4}' -f (Get-Date -Format "s"), $jobName, $manifest.Replace('"', '""'), $rc, $dur) | Out-File -FilePath $doneCsv -Append -Encoding utf8
        if ($rc -ne 0) {
            Write-Log ("FAIL {0} :: {1} (rc={2}, {3}s)" -f $sampleName, $jobName, $rc, $dur)
            throw ("Job failed: {0}" -f $manifest)
        }
        Write-Log ("DONE {0} :: {1} ({2}s)" -f $sampleName, $jobName, $dur)
    }

    Write-Log "Starting postprocess_topo_outputs.py"
    & py -3 "scripts/postprocess_topo_outputs.py" `
        --out-base-list ($wt10Root + ";" + $wt25Root) `
        --report-path $reportPath `
        1>> $outLog 2>> $errLog
    if ($LASTEXITCODE -ne 0) {
        throw "postprocess_topo_outputs.py failed"
    }

    Write-Log "Starting populate_chapter6.py"
    & py -3 "scripts/populate_chapter6.py" `
        --wt10-root $wt10Root `
        --wt25-root $wt25Root `
        --docx-path $chapterPath `
        1>> $outLog 2>> $errLog
    if ($LASTEXITCODE -ne 0) {
        throw "populate_chapter6.py failed"
    }

    Write-Log "Fast corrected rerun pipeline completed successfully."
}
finally {
    Pop-Location
}
