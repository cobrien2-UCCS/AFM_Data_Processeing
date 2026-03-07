param(
    [string]$ResumeRunDir = ""
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

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
if ($ResumeRunDir -and (Test-Path $ResumeRunDir)) {
    $runDir = (Resolve-Path $ResumeRunDir).Path
}
else {
    $runDir = Join-Path $repo ("out\fast_corrected_topo_" + $stamp)
}
$outLog = Join-Path $runDir "fast_corrected_topo.out.log"
$errLog = Join-Path $runDir "fast_corrected_topo.err.log"
$doneCsv = Join-Path $runDir "completed_jobs.csv"
$statusCsv = Join-Path $runDir "job_status.csv"
$manifestListPath = Join-Path $runDir "manifest_list.txt"
$transcriptPath = Join-Path $runDir "wrapper_transcript.txt"
$reportRoot = Split-Path $wt10Root -Parent
$reportPath = Join-Path $reportRoot ("topo_particle_report_FAST_CORRECTED_" + (Split-Path $runDir -Leaf) + ".docx")
$chapterPath = Join-Path $repo ("docs\Thesis\Chapter6_Stage1_Results_Feasibility_DRAFT_fast_corrected_" + (Split-Path $runDir -Leaf) + ".docx")

New-Item -ItemType Directory -Force -Path $runDir | Out-Null
if (-not (Test-Path $doneCsv)) {
    "timestamp,job,manifest,exit_code,duration_seconds" | Out-File -FilePath $doneCsv -Encoding utf8
}
if (-not (Test-Path $statusCsv)) {
    "timestamp,status,sample,job,manifest,message" | Out-File -FilePath $statusCsv -Encoding utf8
}

function Write-Log {
    param([string]$Message)
    $line = ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message)
    $line | Tee-Object -FilePath $outLog -Append | Out-Null
}

function Write-Err {
    param([string]$Message)
    $line = ("[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message)
    $line | Tee-Object -FilePath $errLog -Append | Out-Null
}

function Write-Status {
    param(
        [string]$Status,
        [string]$Sample,
        [string]$Job,
        [string]$Manifest,
        [string]$Message
    )
    ('"{0}","{1}","{2}","{3}","{4}","{5}"' -f
        (Get-Date -Format "s"),
        $Status.Replace('"', '""'),
        $Sample.Replace('"', '""'),
        $Job.Replace('"', '""'),
        $Manifest.Replace('"', '""'),
        $Message.Replace('"', '""')
    ) | Out-File -FilePath $statusCsv -Append -Encoding utf8
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
        Write-Err ("Missing manifest: {0}" -f $ManifestPath)
    }
}

function Get-CompletedManifests {
    param([string]$Path)
    $done = @{}
    if (-not (Test-Path $Path)) {
        return $done
    }
    foreach ($row in (Import-Csv $Path)) {
        if (($row.exit_code -as [int]) -eq 0 -and $row.manifest) {
            $done[$row.manifest] = $true
        }
    }
    return $done
}

function Invoke-ExternalCommand {
    param(
        [string]$FilePath,
        [string[]]$ArgumentList,
        [string]$StdOutPath,
        [string]$StdErrPath,
        [string]$WorkingDirectory
    )
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.WorkingDirectory = $WorkingDirectory
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $quotedArgs = foreach ($arg in $ArgumentList) {
        if ($null -eq $arg) {
            '""'
        }
        elseif ($arg -match '[\s"]') {
            '"' + ($arg -replace '(\\*)"', '$1$1\"') + '"'
        }
        else {
            $arg
        }
    }
    $psi.Arguments = ($quotedArgs -join ' ')

    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $psi
    $stdoutWriter = [System.IO.StreamWriter]::new($StdOutPath, $true)
    $stderrWriter = [System.IO.StreamWriter]::new($StdErrPath, $true)
    try {
        [void]$process.Start()
        $stdoutAsync = $process.StandardOutput.ReadToEndAsync()
        $stderrAsync = $process.StandardError.ReadToEndAsync()
        $process.WaitForExit()
        $stdoutWriter.Write($stdoutAsync.Result)
        $stderrWriter.Write($stderrAsync.Result)
        $stdoutWriter.Flush()
        $stderrWriter.Flush()
        return $process.ExitCode
    }
    finally {
        $stdoutWriter.Dispose()
        $stderrWriter.Dispose()
        if ($process) {
            $process.Dispose()
        }
    }
}

function Get-SampleDirs {
    param([string]$Root)
    $base = Join-Path $Root $systemDir
    if (-not (Test-Path $base)) {
        return @()
    }
    return Get-ChildItem -Directory $base | Where-Object { $_.Name -notmatch '^summary_outputs$' }
}

$global:__wrapperFailed = $false
trap {
    $global:__wrapperFailed = $true
    Write-Err ("Wrapper exception: {0}" -f $_.Exception.Message)
    Write-Err ("At: {0}" -f $_.InvocationInfo.PositionMessage)
    continue
}

Push-Location $repo
Start-Transcript -Path $transcriptPath -Force | Out-Null
try {
    if (-not (Test-Path $py27)) {
        throw "Missing Python 2.7 executable: $py27"
    }
    if (-not (Test-Path $runner)) {
        throw "Missing runner: $runner"
    }

    $completed = Get-CompletedManifests -Path $doneCsv
    if ($completed.Count -gt 0) {
        Write-Log ("Resume mode: found {0} completed manifest(s) in {1}" -f $completed.Count, $doneCsv)
    }

    $manifests = New-Object 'System.Collections.Generic.List[string]'

    foreach ($root in @($wt10Root, $wt25Root)) {
        foreach ($sampleDir in (Get-SampleDirs -Root $root)) {
            $manifest = Join-Path $sampleDir.FullName $primaryJob
            $manifest = Join-Path $manifest "job_manifest.json"
            Add-Manifest -List $manifests -ManifestPath $manifest
        }
    }

    foreach ($entry in $subsetSamples) {
        $sampleRoot = Join-Path (Join-Path $entry.root $systemDir) $entry.sample
        if (-not (Test-Path $sampleRoot)) {
            Write-Err ("Missing subset sample root: {0}" -f $sampleRoot)
            continue
        }
        Get-ChildItem -Directory $sampleRoot |
            Where-Object { $_.Name -like 'particle_forward_*' } |
            ForEach-Object {
                $manifest = Join-Path $_.FullName "job_manifest.json"
                Add-Manifest -List $manifests -ManifestPath $manifest
            }
    }

    $manifestList = $manifests | Sort-Object -Unique
    $manifestList | Out-File -FilePath $manifestListPath -Encoding utf8
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

        if ($completed.ContainsKey($manifest)) {
            Write-Log ("[{0}/{1}] SKIP {2} :: {3} (already completed in run dir)" -f $index, $total, $sampleName, $jobName)
            Write-Status -Status "skip" -Sample $sampleName -Job $jobName -Manifest $manifest -Message "already completed"
            continue
        }

        $start = Get-Date
        Write-Log ("[{0}/{1}] START {2} :: {3}" -f $index, $total, $sampleName, $jobName)
        Write-Status -Status "start" -Sample $sampleName -Job $jobName -Manifest $manifest -Message "launched"

        $rc = Invoke-ExternalCommand `
            -FilePath $py27 `
            -ArgumentList @($runner, "--manifest", $manifest) `
            -StdOutPath $outLog `
            -StdErrPath $errLog `
            -WorkingDirectory $repo
        $dur = [int]((Get-Date) - $start).TotalSeconds
        ('"{0}","{1}","{2}",{3},{4}' -f (Get-Date -Format "s"), $jobName, $manifest.Replace('"', '""'), $rc, $dur) | Out-File -FilePath $doneCsv -Append -Encoding utf8
        if ($rc -ne 0) {
            Write-Log ("FAIL {0} :: {1} (rc={2}, {3}s)" -f $sampleName, $jobName, $rc, $dur)
            Write-Status -Status "fail" -Sample $sampleName -Job $jobName -Manifest $manifest -Message ("rc={0}" -f $rc)
            throw ("Job failed: {0}" -f $manifest)
        }
        Write-Log ("DONE {0} :: {1} ({2}s)" -f $sampleName, $jobName, $dur)
        Write-Status -Status "done" -Sample $sampleName -Job $jobName -Manifest $manifest -Message ("duration={0}s" -f $dur)
    }

    Write-Log "Starting postprocess_topo_outputs.py"
    Write-Status -Status "phase" -Sample "" -Job "" -Manifest "" -Message "postprocess_topo_outputs.py"
    $rc = Invoke-ExternalCommand `
        -FilePath "py" `
        -ArgumentList @("-3", "scripts/postprocess_topo_outputs.py", "--out-base-list", ($wt10Root + ";" + $wt25Root), "--report-path", $reportPath) `
        -StdOutPath $outLog `
        -StdErrPath $errLog `
        -WorkingDirectory $repo
    if ($rc -ne 0) {
        throw "postprocess_topo_outputs.py failed"
    }

    Write-Log "Starting populate_chapter6.py"
    Write-Status -Status "phase" -Sample "" -Job "" -Manifest "" -Message "populate_chapter6.py"
    $rc = Invoke-ExternalCommand `
        -FilePath "py" `
        -ArgumentList @("-3", "scripts/populate_chapter6.py", "--wt10-root", $wt10Root, "--wt25-root", $wt25Root, "--docx-path", $chapterPath) `
        -StdOutPath $outLog `
        -StdErrPath $errLog `
        -WorkingDirectory $repo
    if ($rc -ne 0) {
        throw "populate_chapter6.py failed"
    }

    Write-Log "Fast corrected rerun pipeline completed successfully."
    Write-Status -Status "complete" -Sample "" -Job "" -Manifest "" -Message "pipeline completed"
}
finally {
    Stop-Transcript | Out-Null
    Pop-Location
}
