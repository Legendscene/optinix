# Run this as Administrator: Right-click > Run with PowerShell
Write-Host "=== Network Optimization Script ===" -ForegroundColor Cyan

# Flush DNS
ipconfig /flushdns
Write-Host "[OK] DNS Flushed" -ForegroundColor Green

# TCP/IP optimizations
netsh int tcp set global autotuninglevel=normal
netsh int tcp set global ecncapability=disabled
netsh int tcp set global timestamps=disabled
netsh int tcp set global rss=enabled
netsh int tcp set global rsc=disabled
netsh int tcp set global hystart=disabled
netsh int tcp set global pacingprofile=off
netsh int tcp set global initialrto=300
netsh int tcp set global nonsackrttresiliency=disabled
netsh int tcp set global maxsynretransmissions=2
netsh int tcp set global fastopen=enabled
Write-Host "[OK] TCP Tuned for speed" -ForegroundColor Green

# Disable Nagle's Algorithm (reduces latency)
$interfaces = Get-ChildItem "HKLM:\SYSTEM\CurrentControlSet\Services\Tcpip\Parameters\Interfaces" -ErrorAction SilentlyContinue
foreach($iface in $interfaces) {
    Set-ItemProperty -Path $iface.PSPath -Name "TcpAckFrequency" -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue
    Set-ItemProperty -Path $iface.PSPath -Name "TCPNoDelay" -Value 1 -Type DWord -Force -ErrorAction SilentlyContinue
}
Write-Host "[OK] Nagle's Algorithm Disabled (lower latency)" -ForegroundColor Green

# Disable Wi-Fi Sense
reg add "HKLM\SOFTWARE\Microsoft\WcmSvc\wifinetworkmanager\config" /v AutoConnectAllowedOEM /t REG_DWORD /d 0 /f 2>$null
Write-Host "[OK] Wi-Fi Sense Disabled" -ForegroundColor Green

# Power plan - High Performance
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c 2>$null
powercfg /change monitor-timeout-ac 10
powercfg /change standby-timeout-ac 0
Write-Host "[OK] High Performance Power Plan Set" -ForegroundColor Green

Write-Host "`n=== Done! Restart PC for full effect ===" -ForegroundColor Yellow
Write-Host "Press any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
