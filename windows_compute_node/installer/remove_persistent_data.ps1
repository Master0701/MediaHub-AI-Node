Add-Type -AssemblyName System.Windows.Forms

# ------------------------------------------------------------
# Administratorrechte sicherstellen
# ------------------------------------------------------------

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)

$isAdmin = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdmin) {
    try {
        Start-Process `
            -FilePath "powershell.exe" `
            -ArgumentList @(
                "-NoProfile"
                "-ExecutionPolicy"
                "Bypass"
                "-File"
                "`"$($MyInvocation.MyCommand.Path)`""
            ) `
            -Verb RunAs

        exit 0
    }
    catch {
        [System.Windows.Forms.MessageBox]::Show(
            "Zum Entfernen der gespeicherten Daten werden Administratorrechte benötigt.",
            "MediaHub Compute Node",
            [System.Windows.Forms.MessageBoxButtons]::OK,
            [System.Windows.Forms.MessageBoxIcon]::Warning
        ) | Out-Null

        exit 1
    }
}

# ------------------------------------------------------------
# Pfade
# ------------------------------------------------------------

$runtime = Join-Path $env:ProgramData "MediaHub\ComputeNode"

$uninstallKey = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\MediaHubComputeNodePersistentData"

# ------------------------------------------------------------
# Sicherheitsabfrage
# ------------------------------------------------------------

$result = [System.Windows.Forms.MessageBox]::Show(
    "Sollen die gespeicherten Daten des MediaHub Compute Node wirklich vollständig entfernt werden?`r`n`r`nDazu gehören Einstellungen, Node-ID, Pairing-Daten, API-Token, Jobs, Logs und installierte Compute-Plugins.`r`n`r`nDieser Vorgang kann nicht rückgängig gemacht werden.",
    "MediaHub Compute Node – gespeicherte Daten entfernen",
    [System.Windows.Forms.MessageBoxButtons]::YesNo,
    [System.Windows.Forms.MessageBoxIcon]::Warning,
    [System.Windows.Forms.MessageBoxDefaultButton]::Button2
)

if ($result -ne [System.Windows.Forms.DialogResult]::Yes) {
    exit 0
}

try {
    # Falls doch noch ein Compute Node läuft, beenden.
    Get-Process `
        -Name "MediaHub-Compute-Node" `
        -ErrorAction SilentlyContinue |
        Stop-Process `
            -Force `
            -ErrorAction SilentlyContinue

    # Eigenen Eintrag unter "Installierte Apps" entfernen.
    if (Test-Path $uninstallKey) {
        Remove-Item `
            -Path $uninstallKey `
            -Recurse `
            -Force `
            -ErrorAction Stop
    }

    $self = $MyInvocation.MyCommand.Path

    # Alles im persistenten Ordner außer diesem Skript löschen.
    if (Test-Path $runtime) {
        Get-ChildItem `
            -LiteralPath $runtime `
            -Force `
            -ErrorAction SilentlyContinue |
            Where-Object {
                $_.FullName -ne $self
            } |
            Remove-Item `
                -Recurse `
                -Force `
                -ErrorAction Stop
    }

    [System.Windows.Forms.MessageBox]::Show(
        "Die gespeicherten Daten des MediaHub Compute Node wurden entfernt.",
        "MediaHub Compute Node",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null

    # Das laufende Skript kann sich nicht direkt selbst löschen.
    # Daher übernimmt cmd.exe nach dem Beenden.
    $mediaHubDir = Join-Path $env:ProgramData "MediaHub"

    $cmd = @(
        'timeout /T 2 /NOBREAK >nul'
        "del /F /Q `"$self`""
        "rmdir `"$runtime`" 2>nul"
        "rmdir `"$mediaHubDir`" 2>nul"
    ) -join ' & '

    Start-Process `
        -FilePath $env:ComSpec `
        -ArgumentList "/C $cmd" `
        -WindowStyle Hidden

    exit 0
}
catch {
    [System.Windows.Forms.MessageBox]::Show(
        "Die gespeicherten Daten konnten nicht vollständig entfernt werden.`r`n`r`n$($_.Exception.Message)",
        "MediaHub Compute Node",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null

    exit 1
}
