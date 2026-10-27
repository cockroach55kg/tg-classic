param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
if ($env:GITHUB_ACTIONS -ne 'true') { throw 'This destructive install/uninstall test only runs in an ephemeral GitHub Actions VM.' }
$setup = (Resolve-Path $Installer).Path
$out = Split-Path $setup -Parent
$manifest = Get-Content (Join-Path $PSScriptRoot 'installer-manifest.json') -Raw | ConvertFrom-Json
$app = Join-Path $env:LOCALAPPDATA 'Programs/TG Classic'
$profile = Join-Path $env:APPDATA 'TG Classic'
$programs = [Environment]::GetFolderPath('Programs')
$desktop = [Environment]::GetFolderPath('Desktop')
$startShortcut = Join-Path $programs 'TG Classic.lnk'
$desktopShortcut = Join-Path $desktop 'TG Classic.lnk'
$registry = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\{F58E5C0A-50CA-43FD-91F4-773CE1D70C8B}_is1'
foreach ($path in @($app,$profile,$startShortcut,$desktopShortcut,$registry)) {
    if (Test-Path -LiteralPath $path) { throw "Refusing to change a preexisting app/profile/shortcut: $path" }
}
function Invoke-Setup([string]$Log) {
    $process = Start-Process -FilePath $setup -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-','/LANG=english','/TASKS=desktopicon',('/LOG="' + $Log + '"')) -PassThru -Wait
    if ($process.ExitCode -ne 0) { throw "Setup failed: $($process.ExitCode)" }
}
Invoke-Setup (Join-Path $out 'install.log')
$exe = Join-Path $app 'TG Classic.exe'
if ((Get-FileHash $exe -Algorithm SHA256).Hash.ToLower() -ne $manifest.binary_sha256) { throw 'Installed executable checksum mismatch.' }
if (-not (Test-Path -LiteralPath $profile)) { throw 'Separate data directory was not created.' }
$entry = Get-ItemProperty -LiteralPath $registry
if ($entry.DisplayName -ne 'TG Classic') { throw 'Uninstall registry entry missing.' }
$shell = New-Object -ComObject WScript.Shell
foreach ($path in @($startShortcut,$desktopShortcut)) {
    if (-not (Test-Path -LiteralPath $path)) { throw "Missing shortcut: $path" }
    $shortcut = $shell.CreateShortcut($path)
    if ($shortcut.TargetPath -ne $exe -or $shortcut.WorkingDirectory -ne $profile -or $shortcut.Arguments -ne ('-workdir "' + $profile + '"')) { throw "Incorrect shortcut: $path" }
}
$sentinel = Join-Path $profile 'installer-preservation-test.txt'
'TG Classic installer test data' | Set-Content $sentinel -Encoding utf8
$sentinelHash = (Get-FileHash $sentinel -Algorithm SHA256).Hash
Invoke-Setup (Join-Path $out 'update.log')
if ((Get-FileHash $sentinel -Algorithm SHA256).Hash -ne $sentinelHash) { throw 'Update changed the test profile.' }
& (Join-Path $PSScriptRoot 'verify.ps1') -Executable $exe -Profile $profile -EvidenceDirectory $out
if ((Get-FileHash $exe -Algorithm SHA256).Hash.ToLower() -ne $manifest.binary_sha256) { throw 'Executable changed during verification.' }
$uninstaller = Join-Path $app 'unins000.exe'
$process = Start-Process -FilePath $uninstaller -ArgumentList @('/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART',('/LOG="' + (Join-Path $out 'uninstall.log') + '"')) -PassThru -Wait
if ($process.ExitCode -ne 0) { throw "Uninstall failed: $($process.ExitCode)" }
foreach ($path in @($exe,$startShortcut,$desktopShortcut,$registry)) {
    if (Test-Path -LiteralPath $path) { throw "Uninstall left a registered file or shortcut: $path" }
}
if ((Get-FileHash $sentinel -Algorithm SHA256).Hash -ne $sentinelHash) { throw 'Uninstall removed the test profile.' }
@{
    installer_sha256 = (Get-FileHash $setup -Algorithm SHA256).Hash.ToLower()
    installed_binary_sha256 = $manifest.binary_sha256
    install_succeeded = $true
    current_user_scope = $true
    start_menu_and_desktop_shortcuts_checked = $true
    update_succeeded = $true
    test_profile_preserved_on_update = $true
    native_window_and_15_second_startup = $true
    uninstall_succeeded = $true
    test_profile_preserved_on_uninstall = $true
    real_account_used = $false
} | ConvertTo-Json | Set-Content (Join-Path $out 'installer-verification.json') -Encoding utf8
Write-Output 'Installer, update, native startup, shortcuts and uninstall passed; the test profile was preserved.'
