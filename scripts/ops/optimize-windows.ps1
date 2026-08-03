#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Windows 11 tuning script for gaming + coding on a Ryzen 7 5700X with 64 GB RAM.
.DESCRIPTION
    Applies conservative, reversible optimizations:
      - High-performance power plan
      - Game Mode on
      - Disables visual effects for best performance
      - Disables Hibernation (frees disk space)
      - Sets Windows pagefile to a fixed size on the fastest drive
      - Disables SysMain (Superfetch) to reduce background I/O
      - Stops non-essential telemetry/services for coding workloads
      - Reports what was changed so you can undo via Settings/GUI.
.NOTES
    Restart after running. Some changes require admin rights.
#>

param(
    [string]$PagefileDrive = "C",
    [int]$PagefileMinMB = 8192,
    [int]$PagefileMaxMB = 16384
)

$ErrorActionPreference = "Stop"

function Set-PowerPlanHighPerformance {
    Write-Host "[Power] Setting High performance plan..." -ForegroundColor Cyan
    powercfg /s 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
    if ($LASTEXITCODE -ne 0) {
        powercfg -duplicatescheme e9a42b02-d5df-448d-aa00-03f14749eb61 2>$null | Out-Null
        powercfg /s e9a42b02-d5df-448d-aa00-03f14749eb61 2>$null
    }
}

function Set-GameMode {
    Write-Host "[Gaming] Enabling Game Mode..." -ForegroundColor Cyan
    $path = "HKCU:\Software\Microsoft\GameBar"
    if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name "AllowAutoGameMode" -Value 1 -Type DWord -Force
    Set-ItemProperty -Path $path -Name "AutoGameModeEnabled" -Value 1 -Type DWord -Force
}

function Set-VisualEffectsPerformance {
    Write-Host "[Visuals] Best performance visual effects..." -ForegroundColor Cyan
    $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\VisualEffects"
    if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name "VisualFXSetting" -Value 2 -Type DWord -Force
}

function Disable-Hibernation {
    Write-Host "[Disk] Disabling Hibernation..." -ForegroundColor Cyan
    powercfg /hibernate off 2>&1 | Out-Null
}

function Set-Pagefile {
    param([string]$Drive, [int]$MinMB, [int]$MaxMB)
    Write-Host "[Pagefile] Setting fixed pagefile on ${Drive}: (${MinMB}-${MaxMB} MB)..." -ForegroundColor Cyan

    # First disable automatic management on all drives
    $computer = Get-WmiObject Win32_ComputerSystem
    $computer.AutomaticManagedPagefile = $false
    $computer.Put() | Out-Null

    # Remove pagefiles from other drives
    Get-WmiObject Win32_PageFileSetting | ForEach-Object {
        $_ | Remove-WmiObject
    }

    $pagefilePath = "${Drive}:\pagefile.sys"
    if (Test-Path $pagefilePath) { Remove-Item $pagefilePath -Force -ErrorAction SilentlyContinue }

    Set-WmiInstance -Class Win32_PageFileSetting -Arguments @{Name=$pagefilePath; InitialSize=$MinMB; MaximumSize=$MaxMB} | Out-Null
}

function Disable-SysMain {
    Write-Host "[Services] Disabling SysMain (Superfetch)..." -ForegroundColor Cyan
    Stop-Service -Name "SysMain" -Force -ErrorAction SilentlyContinue
    Set-Service -Name "SysMain" -StartupType Disabled -ErrorAction SilentlyContinue
}

function Disable-TelemetryServices {
    Write-Host "[Services] Disabling non-essential telemetry services..." -ForegroundColor Cyan
    $services = @("DiagTrack", "dmwappushservice", "MapsBroker", "WMPNetworkSvc")
    foreach ($svc in $services) {
        $s = Get-Service -Name $svc -ErrorAction SilentlyContinue
        if ($s) {
            Stop-Service -Name $svc -Force -ErrorAction SilentlyContinue
            Set-Service -Name $svc -StartupType Disabled -ErrorAction SilentlyContinue
            Write-Host "    Disabled $svc"
        }
    }
}

function Disable-WindowsSearchIndexing {
    Write-Host "[Search] Disabling Windows Search indexing (can be re-enabled if needed)..." -ForegroundColor Cyan
    Stop-Service -Name "WSearch" -Force -ErrorAction SilentlyContinue
    Set-Service -Name "WSearch" -StartupType Disabled -ErrorAction SilentlyContinue
}

function Enable-DeveloperMode {
    Write-Host "[Dev] Enabling Developer Mode..." -ForegroundColor Cyan
    $path = "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
    if (!(Test-Path $path)) { New-Item -Path $path -Force | Out-Null }
    Set-ItemProperty -Path $path -Name "AllowDevelopmentWithoutDevLicense" -Value 1 -Type DWord -Force
}

function Show-Summary {
    Write-Host "`n=== Summary ===" -ForegroundColor Green
    Write-Host "Restart your PC for all changes to take effect."
    Write-Host "To revert pagefile:  System Properties -> Advanced -> Performance -> Advanced -> Virtual Memory -> System managed."
    Write-Host "To revert services:  Run 'services.msc' and set StartupType to Automatic/Manual."
    Write-Host "To revert Game Mode: Settings -> Gaming -> Game Mode -> Off."
    Write-Host "To revert power plan: Settings -> System -> Power & battery -> Power mode."
}

Set-PowerPlanHighPerformance
Set-GameMode
Set-VisualEffectsPerformance
Disable-Hibernation
Set-Pagefile -Drive $PagefileDrive -MinMB $PagefileMinMB -MaxMB $PagefileMaxMB
Disable-SysMain
Disable-TelemetryServices
Disable-WindowsSearchIndexing
Enable-DeveloperMode
Show-Summary
