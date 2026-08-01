[CmdletBinding()]
param(
    [string]$SdkDir = $env:STEAMWORKS_SDK_DIR,
    [string[]]$PythonVersions = @("3.9", "3.10", "3.11", "3.12", "3.13", "3.14", "3.15"),
    [string]$Wheelhouse = "",
    [switch]$SkipDependencyInstall,
    [switch]$KeepBuildArtifacts
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

Add-Type -AssemblyName System.IO.Compression.FileSystem

function Test-WheelContents {
    param([Parameter(Mandatory = $true)][string]$WheelPath)

    $Archive = [System.IO.Compression.ZipFile]::OpenRead($WheelPath)
    try {
        $Names = @($Archive.Entries | ForEach-Object { $_.FullName })
        $RuntimeDlls = @($Names | Where-Object { $_ -eq "steamworks/steam_api64.dll" })
        if ($RuntimeDlls.Count -ne 1) {
            throw "Wheel must contain exactly one steamworks/steam_api64.dll."
        }

        $Forbidden = @(
            $Names | Where-Object {
                $_ -match '(^|/)sdk(_|/)' -or
                $_ -match '\.h$' -or
                $_ -match 'steam_api\.json$' -or
                $_ -match '\.lib$'
            }
        )
        if ($Forbidden.Count -gt 0) {
            throw "Wheel contains forbidden SDK files: $($Forbidden -join ', ')"
        }
    }
    finally {
        $Archive.Dispose()
    }
}

$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if ([string]::IsNullOrWhiteSpace($SdkDir)) {
    $SdkDir = Join-Path $RootDir "sdk"
}
$SdkDir = [System.IO.Path]::GetFullPath($SdkDir)

if ([string]::IsNullOrWhiteSpace($Wheelhouse)) {
    $Wheelhouse = Join-Path $RootDir "wheelhouse"
}
$Wheelhouse = [System.IO.Path]::GetFullPath($Wheelhouse)

$ApiJson = Join-Path $SdkDir "public\steam\steam_api.json"
$SteamDll = Join-Path $SdkDir "redistributable_bin\win64\steam_api64.dll"
$SteamLib = Join-Path $SdkDir "redistributable_bin\win64\steam_api64.lib"

foreach ($RequiredPath in @($ApiJson, $SteamDll, $SteamLib)) {
    if (-not (Test-Path -LiteralPath $RequiredPath -PathType Leaf)) {
        throw "Steamworks SDK file not found: $RequiredPath"
    }
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher for Windows ('py.exe') was not found."
}

New-Item -ItemType Directory -Force -Path $Wheelhouse | Out-Null
Get-ChildItem -LiteralPath $Wheelhouse -Filter "*.whl" -File |
    Remove-Item -Force

$PreviousSdkDir = $env:STEAMWORKS_SDK_DIR
$env:STEAMWORKS_SDK_DIR = $SdkDir

try {
    Push-Location $RootDir
    try {
        foreach ($Version in $PythonVersions) {
            Write-Host "Building SteamworksSwig for CPython $Version (64-bit)"

            & py "-$Version-64" -c "import sys; print(sys.executable)"
            if ($LASTEXITCODE -ne 0) {
                throw "64-bit CPython $Version is not installed or not registered with py.exe."
            }

            if (-not $SkipDependencyInstall) {
                & py "-$Version-64" -m pip install --upgrade `
                    "setuptools>=77" `
                    wheel `
                    build `
                    twine
                if ($LASTEXITCODE -ne 0) {
                    throw "Failed to install build dependencies for CPython $Version."
                }
            }

            if (-not $KeepBuildArtifacts) {
                Remove-Item -Recurse -Force -ErrorAction SilentlyContinue `
                    "build", "generated"
                Remove-Item -Force -ErrorAction SilentlyContinue `
                    "python\steamworks\_steamworks*.pyd", `
                    "python\steamworks\steam_api*.dll"
            }

            $RawWheelDir = Join-Path $env:TEMP "steamworks-swig-$($Version.Replace('.', ''))"
            Remove-Item -Recurse -Force -ErrorAction SilentlyContinue $RawWheelDir
            New-Item -ItemType Directory -Force -Path $RawWheelDir | Out-Null

            & py "-$Version-64" -m build `
                --wheel `
                --no-isolation `
                --skip-dependency-check `
                --outdir $RawWheelDir
            if ($LASTEXITCODE -ne 0) {
                throw "Wheel build failed for CPython $Version."
            }

            $Wheels = @(Get-ChildItem -LiteralPath $RawWheelDir -Filter "*.whl" -File)
            if ($Wheels.Count -ne 1) {
                throw "Expected one wheel for CPython $Version; found $($Wheels.Count)."
            }

            $Wheel = $Wheels[0]
            if ($Wheel.Name -notmatch "-cp\d+-cp\d+-win_amd64\.whl$") {
                throw "Unexpected wheel platform tag: $($Wheel.Name)"
            }

            Test-WheelContents -WheelPath $Wheel.FullName

            & py "-$Version-64" -m twine check $Wheel.FullName
            if ($LASTEXITCODE -ne 0) {
                throw "Twine validation failed for $($Wheel.Name)."
            }

            Copy-Item -LiteralPath $Wheel.FullName -Destination $Wheelhouse
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    $env:STEAMWORKS_SDK_DIR = $PreviousSdkDir
}

Write-Host "Built Windows wheels:"
Get-ChildItem -LiteralPath $Wheelhouse -Filter "*.whl" -File |
    Sort-Object Name |
    ForEach-Object { Write-Host "  $($_.FullName)" }
