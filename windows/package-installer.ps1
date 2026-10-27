param(
    [Parameter(Mandatory=$true)][string]$Archive,
    [string]$Destination = (Join-Path $PSScriptRoot '../artifacts/windows-installer')
)
$ErrorActionPreference = 'Stop'
$manifest = Get-Content (Join-Path $PSScriptRoot 'installer-manifest.json') -Raw | ConvertFrom-Json
$archivePath = (Resolve-Path $Archive).Path
if ((Get-FileHash $archivePath -Algorithm SHA256).Hash.ToLower() -ne $manifest.source_zip_sha256) {
    throw 'The portable ZIP does not match the pinned verified Windows build.'
}
$target = [IO.Path]::GetFullPath($Destination)
if (Test-Path $target) { throw "Preserve the previous installer output first: $target" }
$icon = Join-Path $PSScriptRoot 'installer-assets/TG Classic.ico'
if ((Get-FileHash $icon -Algorithm SHA256).Hash.ToLower() -ne $manifest.icon_sha256) { throw 'Installer icon checksum mismatch.' }
$compiler = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6/ISCC.exe'
if (-not (Test-Path $compiler)) { throw 'Inno Setup 6 is required.' }
$stage = Join-Path ([IO.Path]::GetTempPath()) ('TGClassic-installer-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory $stage | Out-Null
try {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [IO.Compression.ZipFile]::OpenRead($archivePath)
    try {
        $actual = @($zip.Entries | Where-Object { $_.Name } | ForEach-Object { $_.FullName.Replace('\','/') } | Sort-Object)
        $expected = @('TG Classic/TG Classic.exe','TG Classic/LICENSE.txt','TG Classic/README.txt','TG Classic/build-info.json') | Sort-Object
        if (Compare-Object $expected $actual) { throw 'Unexpected portable package contents.' }
    } finally { $zip.Dispose() }
    Expand-Archive -LiteralPath $archivePath -DestinationPath $stage
    $payload = Join-Path $stage 'TG Classic'
    $binary = Join-Path $payload 'TG Classic.exe'
    if ((Get-FileHash $binary -Algorithm SHA256).Hash.ToLower() -ne $manifest.binary_sha256) { throw 'Executable checksum mismatch.' }
    New-Item -ItemType Directory $target | Out-Null
    & $compiler "/DPayloadDir=$payload" "/DOutputPath=$target" "/DInstallerVersion=$($manifest.installer_version)" (Join-Path $PSScriptRoot 'installer.iss')
    if ($LASTEXITCODE) { throw "Installer compilation failed: $LASTEXITCODE" }
    $setup = Join-Path $target 'TG-Classic-Windows-x64-Setup.exe'
    $info = @{
        file = [IO.Path]::GetFileName($setup)
        sha256 = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
        bytes = (Get-Item $setup).Length
        source_zip_sha256 = $manifest.source_zip_sha256
        binary_sha256 = $manifest.binary_sha256
        source_build_commit = $manifest.source_build_commit
        installer_version = $manifest.installer_version
        compiler_version = (Get-Item $compiler).VersionInfo.FileVersion
        authenticode_signed = $false
        install_scope = 'current user'
        profile_directory = '%APPDATA%\TG Classic'
    }
    $info | ConvertTo-Json | Set-Content (Join-Path $target 'package-info.json') -Encoding utf8
    ($info.sha256 + '  ' + $info.file) | Set-Content (Join-Path $target 'SHA256SUMS.txt') -Encoding ascii
} finally { Remove-Item -LiteralPath $stage -Recurse -Force }
