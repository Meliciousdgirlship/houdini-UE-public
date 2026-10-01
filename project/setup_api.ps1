$ErrorActionPreference = 'Stop'
$existingPath = Join-Path $PSScriptRoot 'api.local.json'
$existing = if (Test-Path -LiteralPath $existingPath) { Get-Content -LiteralPath $existingPath -Raw | ConvertFrom-Json } else { @{base_url='https://claudex.org/v1';model='deepseek-v4.1-flash'} }
$apiBase = (Read-Host "API Base URL [Enter = $($existing.base_url)]").Trim().TrimEnd('/')
$apiModel = (Read-Host "Model [Enter = $($existing.model)]").Trim()
if (-not $apiBase) { $apiBase = $existing.base_url }
if (-not $apiModel) { $apiModel = $existing.model }
if (-not $apiBase.StartsWith('https://') -or [string]::IsNullOrWhiteSpace($apiModel)) { throw 'HTTPS Base URL and model ID are required.' }
$secret = Read-Host 'API key (hidden input)' -AsSecureString
$secretPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secret)
try {
    $plainKey = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($secretPointer)
    if ([string]::IsNullOrWhiteSpace($plainKey)) { throw 'Key cannot be empty.' }
    [Environment]::SetEnvironmentVariable('BUILDING_API_KEY', $plainKey.Trim(), 'User')
} finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($secretPointer)
    $plainKey = $null
    $secret.Dispose()
}
$apiConfig = @{base_url=$apiBase; model=$apiModel} | ConvertTo-Json
[IO.File]::WriteAllText((Join-Path $PSScriptRoot 'api.local.json'), $apiConfig, [Text.UTF8Encoding]::new($false))
Write-Host 'Saved. No API request was sent. The key was not written into project files.'
Read-Host 'Press Enter to close'
