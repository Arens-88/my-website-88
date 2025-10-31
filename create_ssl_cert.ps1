# 创建SSL证书的PowerShell脚本
# 以管理员身份运行此脚本以生成自签名证书

Write-Host "=====================================" -ForegroundColor Cyan
Write-Host "        生成SSL自签名证书           " -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

# 确保SSL证书目录存在
$sslDir = "D:\ssl_certs"
if (-not (Test-Path $sslDir)) {
    Write-Host "创建SSL证书目录: $sslDir" -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $sslDir -Force | Out-Null
}

# 域名列表
$dnsNames = @("localhost", "tomarens.xyz")
Write-Host "为以下域名生成证书: $($dnsNames -join ', ')" -ForegroundColor Green

# 生成自签名证书
Write-Host "正在生成自签名证书..." -ForegroundColor Yellow
try {
    # 生成证书
    $cert = New-SelfSignedCertificate -DnsName $dnsNames -CertStoreLocation "cert:\LocalMachine\My" -NotAfter (Get-Date).AddYears(1) -KeyLength 2048 -KeyAlgorithm RSA -HashAlgorithm SHA256
    
    # 导出PFX证书
    $pfxPath = "$sslDir\tomarens.pfx"
    $pwd = ConvertTo-SecureString -String "fba_ssl_password" -Force -AsPlainText
    Export-PfxCertificate -Cert $cert -FilePath $pfxPath -Password $pwd -Force | Out-Null
    Write-Host "PFX证书已导出到: $pfxPath" -ForegroundColor Green
    
    # 导出证书文件
    $certPath = "$sslDir\server.crt"
    Export-Certificate -Cert $cert -FilePath $certPath -Type CERT -Force | Out-Null
    Write-Host "证书文件已导出到: $certPath" -ForegroundColor Green
    
    # 提取私钥到server.key
    # 使用OpenSSL命令（如果已安装）
    $keyPath = "$sslDir\server.key"
    
    # 检查OpenSSL是否安装
    $opensslPath = Get-Command "openssl.exe" -ErrorAction SilentlyContinue
    if ($opensslPath) {
        Write-Host "使用OpenSSL提取私钥..." -ForegroundColor Yellow
        & openssl pkcs12 -in $pfxPath -nocerts -out $keyPath -nodes -passin pass:"fba_ssl_password" 2>$null
        
        if (Test-Path $keyPath) {
            Write-Host "私钥已提取到: $keyPath" -ForegroundColor Green
        } else {
            Write-Host "OpenSSL提取私钥失败，尝试备用方法..." -ForegroundColor Red
            
            # 备用方法：使用PowerShell提取（需要PS 7+）
            Write-Host "提示：请手动使用OpenSSL提取私钥，或使用以下命令："
            Write-Host "openssl pkcs12 -in $pfxPath -nocerts -out $keyPath -nodes -passin pass:fba_ssl_password" -ForegroundColor Yellow
        }
    } else {
        Write-Host "未找到OpenSSL，请手动使用OpenSSL提取私钥，或使用以下命令："
        Write-Host "openssl pkcs12 -in $pfxPath -nocerts -out $keyPath -nodes -passin pass:fba_ssl_password" -ForegroundColor Yellow
        Write-Host "您可以从 https://slproweb.com/products/Win32OpenSSL.html 下载OpenSSL" -ForegroundColor Cyan
    }
    
    # 创建证书链文件的软链接或复制
    $certPemPath = "$sslDir\cert.pem"
    $fullchainPemPath = "$sslDir\fullchain.pem"
    
    if (Test-Path $certPath) {
        Copy-Item -Path $certPath -Destination $certPemPath -Force | Out-Null
        Copy-Item -Path $certPath -Destination $fullchainPemPath -Force | Out-Null
        Write-Host "已创建cert.pem和fullchain.pem文件" -ForegroundColor Green
    }
    
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host "证书生成完成！" -ForegroundColor Green
    Write-Host "=====================================" -ForegroundColor Cyan
    Write-Host "证书位置: $sslDir" -ForegroundColor Yellow
    Write-Host "可用域名: $($dnsNames -join ', ')" -ForegroundColor Yellow
    Write-Host "证书有效期: 1年" -ForegroundColor Yellow
    Write-Host "注意：自签名证书在浏览器中会显示安全警告，这是正常的" -ForegroundColor Yellow
    Write-Host "=====================================" -ForegroundColor Cyan
    
    return 0
} catch {
    Write-Host "生成证书时出错: $_" -ForegroundColor Red
    Write-Host "请确保以管理员身份运行此脚本" -ForegroundColor Yellow
    return 1
}