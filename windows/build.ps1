param(
    [Parameter(Mandatory=$true)][string]$Source,
    [string]$Destination = (Join-Path $PSScriptRoot '../artifacts/windows')
)
$ErrorActionPreference = 'Stop'
$sourcePath = (Resolve-Path $Source).Path
$targetPath = [IO.Path]::GetFullPath($Destination)
function Invoke-Checked([scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "Build command failed: $LASTEXITCODE" }
}
if (-not (Get-Command cl.exe -ErrorAction SilentlyContinue)) { throw 'Open the MSVC x64 Native Tools environment first.' }
if (Test-Path $targetPath) { throw "Destination already exists: $targetPath" }
foreach ($name in @('GIT_AUTHOR_NAME','GIT_COMMITTER_NAME')) { if (-not [Environment]::GetEnvironmentVariable($name)) { [Environment]::SetEnvironmentVariable($name,'TG Classic Build') } }
foreach ($name in @('GIT_AUTHOR_EMAIL','GIT_COMMITTER_EMAIL')) { if (-not [Environment]::GetEnvironmentVariable($name)) { [Environment]::SetEnvironmentVariable($name,'tg-classic-build@users.noreply.github.com') } }
$useTestApi = $env:TGCLASSIC_TEST_API -eq 'true'
if (-not $useTestApi -and (-not $env:TGCLASSIC_API_ID -or -not $env:TGCLASSIC_API_HASH)) {
    throw 'Configure TGCLASSIC_API_ID and TGCLASSIC_API_HASH, or explicitly enable TGCLASSIC_TEST_API=true.'
}
Push-Location $sourcePath
try {
    Invoke-Checked { git config user.name 'TG Classic Build' }
    Invoke-Checked { git config user.email 'tg-classic-build@users.noreply.github.com' }
    Invoke-Checked { python (Join-Path $PSScriptRoot 'brand.py') $sourcePath }
    Invoke-Checked { cmd /d /c 'Telegram\build\prepare\win.bat skip-release silent qt6' }
    Push-Location (Join-Path $sourcePath 'Telegram')
    try {
        $api = if ($useTestApi) { @('-D','TDESKTOP_API_TEST=ON') } else {
            @('-D',"TDESKTOP_API_ID=$env:TGCLASSIC_API_ID",'-D',"TDESKTOP_API_HASH=$env:TGCLASSIC_API_HASH")
        }
        Invoke-Checked { python configure.py x64 qt6 @api '-D' 'CMAKE_CONFIGURATION_TYPES=Debug' '-D' 'CMAKE_MSVC_DEBUG_INFORMATION_FORMAT=' '-D' 'DESKTOP_APP_DISABLE_AUTOUPDATE=ON' '-D' 'DESKTOP_APP_DISABLE_CRASH_REPORTS=ON' }
    } finally { Pop-Location }
    Invoke-Checked { cmake --build out --config Debug --target Telegram --parallel 2 }
    $binary = Join-Path $sourcePath 'out/Debug/TG Classic.exe'
    if (-not (Test-Path $binary)) { throw "Missing expected executable: $binary" }
    New-Item -ItemType Directory -Force $targetPath | Out-Null
    $portable = Join-Path $targetPath 'TG Classic'
    New-Item -ItemType Directory $portable | Out-Null
    Copy-Item $binary $portable
    Get-ChildItem (Join-Path $sourcePath 'out/Debug') -File -Filter '*.dll' | Copy-Item -Destination $portable
    Copy-Item (Join-Path $PSScriptRoot '../LICENSE') (Join-Path $portable 'LICENSE.txt')
    $manifest = Get-Content (Join-Path $PSScriptRoot '../manifest.json') -Raw | ConvertFrom-Json
    @{ name='TG Classic'; revision=$manifest.build_revision; architecture='x64'; configuration='Debug'; test_api=$useTestApi; unsigned=$true } | ConvertTo-Json | Set-Content (Join-Path $portable 'build-info.json') -Encoding utf8
    @'
TG Classic for Windows x64
Extract this entire folder, then run TG Classic.exe.
The application is independent of the official Telegram client.
This preview is unsigned. Source: the TG Classic project supplied with this build.
'@ | Set-Content (Join-Path $portable 'README.txt') -Encoding utf8
    $exe = Join-Path $portable 'TG Classic.exe'
    $bytes = [IO.File]::ReadAllBytes($exe)
    if ($bytes[0] -ne 0x4d -or $bytes[1] -ne 0x5a) { throw 'The output is not a Windows PE executable.' }
    $pe = [BitConverter]::ToInt32($bytes, 0x3c)
    if ([BitConverter]::ToUInt16($bytes, $pe+4) -ne 0x8664) { throw 'The executable is not x64.' }
    & (Join-Path $PSScriptRoot 'verify.ps1') -Executable $exe
    $archive = Join-Path $targetPath 'TG-Classic-Windows-x64.zip'
    Compress-Archive -Path $portable -DestinationPath $archive
    (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower() + '  ' + [IO.Path]::GetFileName($archive) | Set-Content (Join-Path $targetPath 'SHA256SUMS.txt')
    Write-Output "Built and packaged: $archive"
} finally { Pop-Location }
