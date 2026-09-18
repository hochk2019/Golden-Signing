$store = New-Object System.Security.Cryptography.X509Certificates.X509Store('My','CurrentUser')
$store.Open('ReadOnly')
Write-Host "count=$($store.Certificates.Count)"
foreach ($c in $store.Certificates) {
  Write-Host ("{0} | PK={1} | After={2}" -f $c.Subject, $c.HasPrivateKey, $c.NotAfter)
}
$store.Close()
