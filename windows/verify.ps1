param(
    [Parameter(Mandatory=$true)][string]$Executable,
    [string]$Profile = '',
    [string]$EvidenceDirectory = ''
)
$ErrorActionPreference = 'Stop'
$binary = (Resolve-Path $Executable).Path
if ($Profile) {
    $profilePath = (Resolve-Path $Profile).Path
} else {
    $profilePath = Join-Path ([IO.Path]::GetTempPath()) ('TGClassic-smoke-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory $profilePath | Out-Null
}
$evidencePath = if ($EvidenceDirectory) { [IO.Path]::GetFullPath($EvidenceDirectory) } else { Split-Path $binary -Parent }
New-Item -ItemType Directory -Force $evidencePath | Out-Null
$process = Start-Process -FilePath $binary -ArgumentList @('-workdir', ('"' + $profilePath + '"')) -WorkingDirectory $profilePath -PassThru
$result = @{ binary=$binary; empty_profile=$profilePath; duration_seconds=15; started=$false; window_created=$false }
try {
    Start-Sleep -Seconds 15
    $process.Refresh()
    if ($process.HasExited) { throw "TG Classic exited during startup with code $($process.ExitCode)." }
    $result.started = $true
    $result.window_created = $process.MainWindowHandle -ne 0
    if (-not $result.window_created) { throw 'The process stayed alive but did not create a main window.' }
    $result.sha256 = (Get-FileHash $binary -Algorithm SHA256).Hash.ToLower()
    Add-Type -AssemblyName System.Drawing
    Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class TGClassicWindowCapture {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr window, out RECT rectangle);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr window, IntPtr dc, uint flags);
}
'@
    $rectangle = New-Object TGClassicWindowCapture+RECT
    if (-not [TGClassicWindowCapture]::GetWindowRect($process.MainWindowHandle, [ref]$rectangle)) { throw 'Could not read the test window bounds.' }
    $width = $rectangle.Right - $rectangle.Left
    $height = $rectangle.Bottom - $rectangle.Top
    if ($width -le 0 -or $height -le 0) { throw 'The test window has no visible area.' }
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $dc = $graphics.GetHdc()
    try {
        if (-not [TGClassicWindowCapture]::PrintWindow($process.MainWindowHandle, $dc, 2)) { throw 'Could not capture the test window.' }
    } finally { $graphics.ReleaseHdc($dc); $graphics.Dispose() }
    try {
        $bitmap.Save((Join-Path $evidencePath 'startup-verification.png'), [System.Drawing.Imaging.ImageFormat]::Png)
    } finally { $bitmap.Dispose() }
    $result.screenshot = 'startup-verification.png'
    $result.window_width = $width
    $result.window_height = $height
} finally {
    # This process was created above in an empty CI profile, not an installed client.
    if (-not $process.HasExited) {
        if ($process.Path -ne $binary) { throw 'Refusing to stop a different executable.' }
        Stop-Process -Id $process.Id
        $process.WaitForExit()
    }
    $result | ConvertTo-Json | Set-Content (Join-Path $evidencePath 'startup-verification.json') -Encoding utf8
}
Write-Output 'TG Classic created a native window and stayed running for 15 seconds with an empty profile.'
