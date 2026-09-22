param(
    [Parameter(Mandatory = $true)]
    [int]$ProcessId,
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,
    [int]$InitialDelayMilliseconds = 0,
    [int]$IntervalMilliseconds = 250,
    [int]$Count = 1
)

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class WindowCaptureNative {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")]
    public static extern bool PrintWindow(IntPtr hWnd, IntPtr hdcBlt, uint flags);
}
"@

$process = Get-Process -Id $ProcessId -ErrorAction Stop
$handle = $process.MainWindowHandle
if ($handle -eq [IntPtr]::Zero) {
    throw "Process does not have a main window"
}

$rect = New-Object WindowCaptureNative+RECT
if (-not [WindowCaptureNative]::GetWindowRect($handle, [ref]$rect)) {
    throw "GetWindowRect failed"
}
$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($InitialDelayMilliseconds -gt 0) {
    Start-Sleep -Milliseconds $InitialDelayMilliseconds
}

$absoluteOutput = [System.IO.Path]::GetFullPath($OutputPath)
$parent = [System.IO.Path]::GetDirectoryName($absoluteOutput)
[System.IO.Directory]::CreateDirectory($parent) | Out-Null
for ($index = 0; $index -lt $Count; $index++) {
    $bitmap = New-Object System.Drawing.Bitmap($width, $height)
    $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
    $hdc = $graphics.GetHdc()
    try {
        if (-not [WindowCaptureNative]::PrintWindow($handle, $hdc, 2)) {
            throw "PrintWindow failed"
        }
    } finally {
        $graphics.ReleaseHdc($hdc)
        $graphics.Dispose()
    }
    if ($Count -eq 1) {
        $frameOutput = $absoluteOutput
    } else {
        $frameOutput = [System.IO.Path]::Combine(
            $parent,
            ([System.IO.Path]::GetFileNameWithoutExtension($absoluteOutput) + ("_{0:D2}" -f $index) + [System.IO.Path]::GetExtension($absoluteOutput))
        )
    }
    $bitmap.Save($frameOutput, [System.Drawing.Imaging.ImageFormat]::Png)
    $bitmap.Dispose()
    [pscustomobject]@{ Output = $frameOutput; Width = $width; Height = $height; Frame = $index }
    if ($index + 1 -lt $Count) {
        Start-Sleep -Milliseconds $IntervalMilliseconds
    }
}
