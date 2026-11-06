[CmdletBinding()]
param(
    [ValidateSet('Inspect', 'Migrate', 'Rollback')]
    [string]$Action = 'Inspect',
    [string]$Source = (Join-Path $env:USERPROFILE '.workbuddy'),
    [string]$Target,
    [string]$StateFile,
    [switch]$Confirmed,
    [switch]$AppClosed,
    [switch]$AcceptNewDataInTarget
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-LocalPath([string]$Path) {
    if ($Path -notmatch '^[A-Za-z]:\\' -or $Path -match '[*?]') {
        throw 'Use an absolute local drive path without wildcards.'
    }
    $full = [IO.Path]::GetFullPath($Path).TrimEnd('\')
    if ($full.Length -le 3) { throw 'A drive root cannot be used as a data directory.' }
    return $full
}

function Assert-NoLinkedAncestor([string]$Path) {
    $cursor = $Path
    while ($cursor) {
        if (Test-Path -LiteralPath $cursor) {
            $item = Get-Item -LiteralPath $cursor -Force
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Reparse point in path: $cursor"
            }
            if (-not $item.PSIsContainer) { throw "Not a directory: $cursor" }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
}

function Assert-OrdinaryDirectory([string]$Path) {
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Expected an ordinary directory: $Path"
    }
}

function Get-Inventory([string]$Root, [switch]$Hash, [string]$Destination) {
    Assert-OrdinaryDirectory $Root
    $stack = New-Object 'Collections.Generic.Stack[string]'
    $stack.Push($Root)
    $files = New-Object 'Collections.Generic.List[object]'
    $directories = New-Object 'Collections.Generic.List[string]'
    [long]$bytes = 0
    while ($stack.Count -gt 0) {
        $directory = $stack.Pop()
        foreach ($item in (Get-Item -LiteralPath $directory -Force).GetFileSystemInfos()) {
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                throw "Internal reparse point requires separate handling: $($item.FullName)"
            }
            if ($item.Name -match '^(?i:CON|PRN|AUX|NUL|COM[0-9]|LPT[0-9])(?:\.|$)' -or
                $item.Name -match '[ .]$') {
                throw "Unsupported Windows name; do not shred it: $($item.FullName)"
            }
            $relative = $item.FullName.Substring($Root.Length + 1)
            $limit = if ($item -is [IO.DirectoryInfo]) { 248 } else { 260 }
            if ($item.FullName.Length -ge $limit -or
                ($Destination -and (Join-Path $Destination $relative).Length -ge $limit)) {
                throw "Long path needs separate handling: $($item.FullName)"
            }
            if ($item -is [IO.DirectoryInfo]) {
                $directories.Add($relative)
                $stack.Push($item.FullName)
            } else {
                $digest = if ($Hash) { (Get-FileHash -LiteralPath $item.FullName -Algorithm SHA256).Hash } else { '' }
                $files.Add([pscustomobject]@{ Path = $relative; Length = $item.Length; Hash = $digest })
                $bytes += $item.Length
            }
        }
    }
    return [pscustomobject]@{
        Directories = @($directories | Sort-Object)
        Files = @($files | Sort-Object Path)
        Bytes = $bytes
        FileCount = $files.Count
    }
}

function Test-InventoryEqual($Left, $Right) {
    return (($Left | ConvertTo-Json -Depth 6 -Compress) -ceq
            ($Right | ConvertTo-Json -Depth 6 -Compress))
}

function Get-WorkBuddyProcesses {
    return @(Get-Process | Where-Object { $_.ProcessName -like '*workbuddy*' } |
        Select-Object ProcessName, Id)
}

function Assert-Stopped {
    if (-not $Confirmed -or -not $AppClosed) {
        throw 'Explicit user confirmation and app-exit declaration are required: -Confirmed -AppClosed.'
    }
    $running = @(Get-WorkBuddyProcesses)
    if ($running.Count -gt 0) {
        throw "Exit WorkBuddy from its tray first. Running process IDs: $(($running.Id) -join ', ')"
    }
}

function Get-TargetDrive([string]$Path) {
    $drive = New-Object IO.DriveInfo ([IO.Path]::GetPathRoot($Path))
    if (-not $drive.IsReady -or $drive.DriveType -ne [IO.DriveType]::Fixed -or $drive.DriveFormat -ne 'NTFS') {
        throw 'Target must be on a ready, local fixed NTFS drive.'
    }
    if ($drive.Name.TrimEnd('\') -ieq $env:SystemDrive) { throw 'Target must be outside the system drive.' }
    return $drive
}

function Assert-Target([string]$From, [string]$To, [long]$Bytes) {
    if ($From -ieq $To -or $To.StartsWith($From + '\', [StringComparison]::OrdinalIgnoreCase) -or
        $From.StartsWith($To + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'Source and target must be separate, non-nested directories.'
    }
    Assert-NoLinkedAncestor $To
    if (Test-Path -LiteralPath $To) {
        if (@(Get-ChildItem -LiteralPath $To -Force).Count -gt 0) { throw 'Target is not empty; it will not be cleared or overwritten.' }
    }
    $drive = Get-TargetDrive $To
    if ($drive.AvailableFreeSpace -lt ($Bytes + 64MB)) { throw 'Insufficient target space (64 MiB minimum reserve).' }
    return $drive
}

function Set-PrivateAcl([string]$Path, [switch]$File) {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $allowed = @($identity.User.Value, 'S-1-5-18', 'S-1-5-32-544') | Select-Object -Unique
    $acl = if ($File) { New-Object Security.AccessControl.FileSecurity } else { New-Object Security.AccessControl.DirectorySecurity }
    $acl.SetOwner($identity.User)
    $acl.SetAccessRuleProtection($true, $false)
    $inheritance = if ($File) { [Security.AccessControl.InheritanceFlags]::None } else {
        [Security.AccessControl.InheritanceFlags]::ContainerInherit -bor [Security.AccessControl.InheritanceFlags]::ObjectInherit
    }
    foreach ($sidText in $allowed) {
        $sid = New-Object Security.Principal.SecurityIdentifier $sidText
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($sid,
            [Security.AccessControl.FileSystemRights]::FullControl, $inheritance,
            [Security.AccessControl.PropagationFlags]::None, [Security.AccessControl.AccessControlType]::Allow)
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $Path -AclObject $acl
    $actual = Get-Acl -LiteralPath $Path
    if (-not $actual.AreAccessRulesProtected) { throw "ACL inheritance is still enabled: $Path" }
    foreach ($rule in $actual.GetAccessRules($true, $true, [Security.Principal.SecurityIdentifier])) {
        if ($rule.AccessControlType -ne 'Allow' -or $rule.IdentityReference.Value -notin $allowed) {
            throw "Unexpected target access rule: $Path"
        }
    }
}

function Assert-Junction([string]$Path, [string]$Expected) {
    $link = Get-Item -LiteralPath $Path -Force
    if (-not $link.PSIsContainer -or $link.LinkType -ne 'Junction' -or @($link.Target).Count -ne 1 -or
        (Get-LocalPath ([string]$link.Target[0])) -ine $Expected) {
        throw "Not the expected junction; do not remove it: $Path"
    }
}

function Save-State($State, [string]$Path) {
    $temp = $Path + '.tmp'
    $json = $State | ConvertTo-Json -Depth 8
    [IO.File]::WriteAllText($temp, $json, (New-Object System.Text.UTF8Encoding($false)))
    if (Test-Path -LiteralPath $Path) {
        [IO.File]::Replace($temp, $Path, $null)
    } else {
        [IO.File]::Move($temp, $Path)
    }
}

if ($Action -eq 'Rollback') {
    Assert-Stopped
    if (-not $StateFile) { throw 'Rollback requires the exact -StateFile from this migration.' }
    $StateFile = Get-LocalPath $StateFile
    $state = Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($state.Version -ne 1 -or $state.Status -ne 'Linked') { throw 'State is not a completed junction migration.' }
    $Source = Get-LocalPath $state.Source
    $Target = Get-LocalPath $state.Target
    $backup = Get-LocalPath $state.Backup
    if ($backup -notlike ($Source + '.backup-*') -or
        [IO.Path]::GetDirectoryName($backup) -ine [IO.Path]::GetDirectoryName($Source) -or
        $StateFile -ine ($backup + '.migration.json')) { throw 'Backup/state paths do not match this migration.' }
    Assert-NoLinkedAncestor $backup
    Assert-NoLinkedAncestor $Target
    Assert-Junction $Source $Target
    if (-not (Test-InventoryEqual $state.Inventory (Get-Inventory $backup -Hash))) {
        throw 'Backup changed; automatic rollback is unsafe.'
    }
    $changed = -not (Test-InventoryEqual $state.Inventory (Get-Inventory $Target -Hash))
    if ($changed -and -not $AcceptNewDataInTarget) {
        throw 'Target has new/changed data. It will be retained but inactive after rollback. Obtain explicit acceptance before using -AcceptNewDataInTarget.'
    }
    # Non-recursive deletion removes only the verified junction, never its target.
    [IO.Directory]::Delete($Source)
    try {
        Move-Item -LiteralPath $backup -Destination $Source
    } catch {
        if (-not (Test-Path -LiteralPath $Source)) { New-Item -ItemType Junction -Path $Source -Target $Target | Out-Null }
        throw
    }
    $state.Status = 'RolledBack'
    Save-State $state $StateFile
    [pscustomobject]@{ Status = 'RolledBack'; Source = $Source; RetainedTarget = $Target; NewDataRetained = $changed; StateFile = $StateFile }
    return
}

$Source = Get-LocalPath $Source
if ([IO.Path]::GetFileName($Source) -ine '.workbuddy') { throw 'Source must be the explicitly scoped .workbuddy directory.' }
if (-not (Test-Path -LiteralPath $Source)) { throw "Source does not exist: $Source" }
if ($Action -eq 'Migrate') { Assert-Stopped }
$sourceItem = Get-Item -LiteralPath $Source -Force
if ($sourceItem.Attributes -band [IO.FileAttributes]::ReparsePoint) {
    if ($Action -eq 'Migrate') { throw 'Source is already linked; do not migrate it again.' }
    [pscustomobject]@{ Status = 'AlreadyLinked'; Source = $Source; LinkType = $sourceItem.LinkType; Target = $sourceItem.Target; RunningProcesses = @(Get-WorkBuddyProcesses) }
    return
}
Assert-NoLinkedAncestor $Source
if ($Target) { $Target = Get-LocalPath $Target }
$inventory = Get-Inventory $Source -Hash:($Action -eq 'Migrate') -Destination $Target
$drive = if ($Target) { Assert-Target $Source $Target $inventory.Bytes } else { $null }
if ($Action -eq 'Inspect') {
    [pscustomobject]@{
        Status = 'Inspected'; Source = $Source; Target = $Target
        Files = $inventory.FileCount; Directories = $inventory.Directories.Count; Bytes = $inventory.Bytes
        TargetFreeBytes = $(if ($drive) { $drive.AvailableFreeSpace } else { $null })
        RunningProcesses = @(Get-WorkBuddyProcesses)
        Note = 'Read-only metadata snapshot. Permissions are enforced when copying; app validation and backup cleanup are separate.'
    }
    return
}
if (-not $Target) { throw 'Migration requires an explicitly selected -Target directory.' }
$robocopy = Join-Path $env:SystemRoot 'System32\robocopy.exe'
if (-not (Test-Path -LiteralPath $robocopy)) { throw 'System robocopy.exe is unavailable.' }
$id = (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$backup = $Source + '.backup-' + $id
$StateFile = $backup + '.migration.json'
if ($backup.Length -ge 248 -or $StateFile.Length -ge 260) { throw 'Backup/state path is too long.' }
# Record recovery paths before copying; a failed copy is retained for inspection.
$state = [pscustomobject]@{
    Version = 1; Status = 'Copying'; Source = $Source; Target = $Target; Backup = $backup
    Inventory = $inventory; Created = (Get-Date).ToString('o')
}
New-Item -ItemType File -Path $StateFile | Out-Null
Set-PrivateAcl $StateFile -File
Save-State $state $StateFile
try {
    if (-not (Test-Path -LiteralPath $Target)) { New-Item -ItemType Directory -Path $Target | Out-Null }
    Set-PrivateAcl $Target
    & $robocopy $Source $Target /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NP /NFL /NDL /NJH /NJS | Out-Host
    $copyCode = $LASTEXITCODE
    if ($copyCode -ge 8) { throw "Robocopy failed with exit code $copyCode. Source remains intact; partial target is retained." }
    Assert-Stopped
    if (-not (Test-InventoryEqual $inventory (Get-Inventory $Source -Hash -Destination $backup))) { throw 'Source changed during copying; no cutover performed.' }
    if (-not (Test-InventoryEqual $inventory (Get-Inventory $Target -Hash))) { throw 'Destination content verification failed; no cutover performed.' }
    $state.Status = 'Verified'
    Save-State $state $StateFile
    Move-Item -LiteralPath $Source -Destination $backup
    try {
        New-Item -ItemType Junction -Path $Source -Target $Target | Out-Null
        Assert-Junction $Source $Target
    } catch {
        if (Test-Path -LiteralPath $Source) {
            Assert-Junction $Source $Target
            [IO.Directory]::Delete($Source)
        }
        Move-Item -LiteralPath $backup -Destination $Source
        throw
    }
    $state.Status = 'Linked'
    Save-State $state $StateFile
} catch {
    Write-Warning "Stopped. Do not delete data. Source: $Source; target: $Target; backup: $backup; state: $StateFile"
    throw
}
[pscustomobject]@{
    Status = 'Linked-AppValidationPending'; Source = $Source; Target = $Target; Backup = $backup
    StateFile = $StateFile; Files = $inventory.FileCount; Bytes = $inventory.Bytes; RobocopyExitCode = $copyCode
    Note = 'SHA-256 and junction checks passed. Old backup still occupies source-drive space. Test WorkBuddy before separately approving cleanup.'
}
