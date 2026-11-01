# Actualiza DATABASE_URL del ambiente de Elastic Beanstalk pidiendo la
# contrasena de RDS de forma oculta. La contrasena no se imprime ni se guarda.
param(
    [string]$EnvironmentName = "blacklist-env",
    [string]$DbHost = "blacklist-db.caj6aqockm6d.us-east-1.rds.amazonaws.com",
    [string]$DbName = "blacklist",
    [string]$DbUser = "postgres"
)

$secure = Read-Host "Contrasena de RDS ($DbUser)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($bstr)
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
}
if ([string]::IsNullOrEmpty($plain)) { Write-Error "Contrasena vacia, no se actualiza nada."; exit 1 }

$url = "postgresql+psycopg2://${DbUser}:$([Uri]::EscapeDataString($plain))@${DbHost}:5432/$DbName"
$settings = @(@{ Namespace = "aws:elasticbeanstalk:application:environment"; OptionName = "DATABASE_URL"; Value = $url })

$tmp = [IO.Path]::GetTempFileName()
try {
    [IO.File]::WriteAllText($tmp, (ConvertTo-Json -InputObject $settings -Compress))
    aws elasticbeanstalk update-environment --environment-name $EnvironmentName --option-settings "file://$tmp" --query "{Status:Status,Env:EnvironmentName}" --output json
} finally {
    Remove-Item $tmp -Force
    $plain = $null; $url = $null
}
Write-Host "Listo. Beanstalk esta aplicando el cambio (1-2 minutos)."
