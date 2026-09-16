Add-Type -AssemblyName System.IO.Compression.FileSystem

$zip = [System.IO.Compression.ZipFile]::OpenRead('KPN TV+.apks')
$baseEntry = $zip.Entries | Where-Object { $_.Name -eq 'base.apk' }

if (-not (Test-Path 'scratch/extracted')) {
    New-Item -ItemType Directory -Path 'scratch/extracted' | Out-Null
}

$baseApkPath = 'scratch/extracted/base.apk'
if (-not (Test-Path $baseApkPath)) {
    [System.IO.Compression.ZipFileExtensions]::ExtractToFile($baseEntry, $baseApkPath, $true)
}
$zip.Dispose()

$baseZip = [System.IO.Compression.ZipFile]::OpenRead($baseApkPath)
Write-Output "=== Assets ==="
$baseZip.Entries | Where-Object { $_.FullName -like 'assets/*' } | Select-Object -First 30 -ExpandProperty FullName

Write-Output "=== Classes DEX ==="
$baseZip.Entries | Where-Object { $_.FullName -like '*.dex' } | Select-Object -ExpandProperty FullName

Write-Output "=== Libs ==="
$baseZip.Entries | Where-Object { $_.FullName -like 'lib/*' } | Select-Object -First 20 -ExpandProperty FullName

$baseZip.Dispose()
