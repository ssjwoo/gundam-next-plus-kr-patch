param([Parameter(Mandatory = $true)][int]$ProcessId)

Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class PpssppWindowNative {
    public delegate bool EnumWindowsCallback(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsCallback callback, IntPtr lParam);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int command);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
}
"@

$targetId = [uint32]$ProcessId
$matches = New-Object 'System.Collections.Generic.List[System.IntPtr]'
$callback = [PpssppWindowNative+EnumWindowsCallback]{
    param([IntPtr]$candidate, [IntPtr]$unused)
    $ownerId = [uint32]0
    [PpssppWindowNative]::GetWindowThreadProcessId($candidate, [ref]$ownerId) | Out-Null
    if ($ownerId -eq $targetId) {
        $title = New-Object System.Text.StringBuilder 256
        [PpssppWindowNative]::GetWindowText($candidate, $title, 256) | Out-Null
        if ($title.ToString().StartsWith('PPSSPP')) { $matches.Add($candidate) }
    }
    return $true
}
[PpssppWindowNative]::EnumWindows($callback, [IntPtr]::Zero) | Out-Null
if ($matches.Count -ne 1) { throw "Expected one PPSSPP window for process $ProcessId, found $($matches.Count)" }
[PpssppWindowNative]::ShowWindow($matches[0], 9) | Out-Null
[PpssppWindowNative]::SetForegroundWindow($matches[0]) | Out-Null
Write-Output "Restored PPSSPP window for process $ProcessId"
