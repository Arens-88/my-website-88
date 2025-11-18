# Windows network diagnostics script - for SSH connection issues
# Usage: Run in PowerShell as administrator: .\network_diagnostics.ps1 -ServerIP 172.28.47.29

param(
    [string]$ServerIP = "172.28.47.29"
)

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "SSH Connection Diagnostic Tool" -ForegroundColor Cyan
Write-Host "Target Server IP: $ServerIP" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# 1. Check local IP configuration
Write-Host "\n1. Local Network Configuration:" -ForegroundColor Green
ipconfig /all | Select-String "IPv4 Address", "Subnet Mask", "Default Gateway"

# 2. Test basic connectivity with server
Write-Host "\n2. Testing Basic Connectivity to Server:" -ForegroundColor Green
try {
    $pingResult = Test-Connection -ComputerName $ServerIP -Count 4 -ErrorAction Stop
    Write-Host "✅ Server is reachable!" -ForegroundColor Green
    $pingResult | Format-Table -Property Address, IPv4Address, ResponseTime, Status
} catch {
    Write-Host "❌ Cannot ping the server, check network connection or firewall settings" -ForegroundColor Red
}

# 3. Check port 22 connectivity
Write-Host "\n3. Testing Port 22 Connectivity:" -ForegroundColor Green
try {
    $portTest = Test-NetConnection -ComputerName $ServerIP -Port 22 -ErrorAction Stop
    if ($portTest.TcpTestSucceeded) {
        Write-Host "✅ Port 22 is accessible!" -ForegroundColor Green
    } else {
        Write-Host "❌ Port 22 connection failed, check if SSH service is running or port is open" -ForegroundColor Red
    }
    $portTest | Format-List -Property ComputerName, RemotePort, TcpTestSucceeded, PingSucceeded
} catch {
    Write-Host "❌ Port test failed: $_" -ForegroundColor Red
}

# 4. Check Windows Firewall status
Write-Host "\n4. Windows Firewall Status:" -ForegroundColor Green
try {
    Get-NetFirewallProfile | Select-Object Name, Enabled
} catch {
    Write-Host "❌ Cannot check firewall status, running as administrator?" -ForegroundColor Red
}

# 5. Check network routes
Write-Host "\n5. Network Route Information:" -ForegroundColor Green
try {
    route print | Select-String -Pattern "$ServerIP", "0.0.0.0"
} catch {
    Write-Host "❌ Cannot display route information" -ForegroundColor Red
}

# 6. Check SSH client
Write-Host "\n6. SSH Client Information:" -ForegroundColor Green
try {
    $sshVersion = ssh -V 2>&1
    Write-Host "✅ OpenSSH client is installed: $sshVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ SSH client not found, please install OpenSSH client" -ForegroundColor Red
    Write-Host "Installation command: Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0" -ForegroundColor Yellow
}

# 7. Display connection suggestions
Write-Host "\n=========================================" -ForegroundColor Cyan
Write-Host "Troubleshooting Suggestions:" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "1. Ensure you're on the same network as the server" -ForegroundColor Yellow
Write-Host "2. Verify the server IP address is correct" -ForegroundColor Yellow
Write-Host "3. Confirm SSH service is running on the server" -ForegroundColor Yellow
Write-Host "4. Check server firewall allows port 22 connections" -ForegroundColor Yellow
Write-Host "5. If using cloud server, check security group configuration" -ForegroundColor Yellow
Write-Host "6. Try temporarily disabling local firewall to test connection" -ForegroundColor Yellow
Write-Host "7. Check if network devices restrict SSH connections" -ForegroundColor Yellow
Write-Host "\nAlternative Solutions:" -ForegroundColor Yellow
Write-Host "- Use Web SSH via cloud service console" -ForegroundColor Yellow
Write-Host "- Use FTP service instead of SSH for file transfer" -ForegroundColor Yellow
Write-Host "- Use shared folders if supported" -ForegroundColor Yellow
Write-Host "- Use cloud storage service for file transfer" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan