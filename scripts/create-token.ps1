# Genera el Bearer token (JWT HS256) equivalente a `flask create-token`
# sin necesidad de Python. Lee JWT_SECRET_KEY y STATIC_API_TOKEN del .env
# y guarda el token en la variable BEARER_TOKEN del mismo .env.
param([string]$EnvFile = (Join-Path $PSScriptRoot "..\.env"))

$vars = @{}
Get-Content $EnvFile | Where-Object { $_ -match '^\s*([A-Z_]+)=(.*)$' } | ForEach-Object { $vars[$Matches[1]] = $Matches[2] }
foreach ($k in "JWT_SECRET_KEY", "STATIC_API_TOKEN") {
    if (-not $vars[$k]) { Write-Error "Falta $k en $EnvFile"; exit 1 }
}

function ConvertTo-Base64Url([byte[]]$bytes) {
    [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$header = '{"alg":"HS256","typ":"JWT"}'
# Mismos claims que create_access_token de Flask-JWT-Extended (expira en 3650 dias).
$payload = ConvertTo-Json -Compress -InputObject ([ordered]@{
    fresh = $false; iat = $now; jti = [guid]::NewGuid().ToString(); type = "access"
    sub = $vars["STATIC_API_TOKEN"]; nbf = $now; exp = $now + 3650 * 86400
})

$utf8 = [Text.Encoding]::UTF8
$unsigned = (ConvertTo-Base64Url $utf8.GetBytes($header)) + "." + (ConvertTo-Base64Url $utf8.GetBytes($payload))
$hmac = New-Object Security.Cryptography.HMACSHA256 (, $utf8.GetBytes($vars["JWT_SECRET_KEY"]))
$token = $unsigned + "." + (ConvertTo-Base64Url $hmac.ComputeHash($utf8.GetBytes($unsigned)))

$lines = @(Get-Content $EnvFile | Where-Object { $_ -notmatch '^BEARER_TOKEN=' }) + "BEARER_TOKEN=$token"
Set-Content -Path $EnvFile -Value $lines -Encoding ascii
Write-Host "Token generado y guardado como BEARER_TOKEN en $EnvFile"
