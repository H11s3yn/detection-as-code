# run-atomics.ps1 — Modul D atomic simulyasiyasi (VM2, pre-atomic snapshot-dan sonra)
# Istifade: Administrator PowerShell-de  ->  powershell -ExecutionPolicy Bypass -File .\run-atomics.ps1
Import-Module invoke-atomicredteam -Force

# Qayda -> atomic test xeritesi (15 isledilebilen test)
$tests = @(
  @{ t="T1033";     n=8;  rule="whoami" },
  @{ t="T1136.001"; n=4;  rule="net user add" },
  @{ t="T1685";     n=19; rule="Defender disable" },
  @{ t="T1047";     n=5;  rule="wmic proc create" },
  @{ t="T1082";     n=1;  rule="systeminfo" },
  @{ t="T1003.002"; n=1;  rule="reg save SAM" },
  @{ t="T1053.005"; n=2;  rule="schtasks create" },
  @{ t="T1543.003"; n=2;  rule="sc create service" },
  @{ t="T1547.001"; n=1;  rule="run key" },
  @{ t="T1105";     n=9;  rule="bitsadmin download" },
  @{ t="T1059.001"; n=15; rule="ps encoded" },
  @{ t="T1069.002"; n=3;  rule="net group DA" },
  @{ t="T1482";     n=2;  rule="nltest trusts" },
  @{ t="T1003.001"; n=2;  rule="LSASS comsvcs" },
  @{ t="T1021.002"; n=3;  rule="PsExec" }
)

"BASLANDI: $(Get-Date -Format HH:mm:ss)"
foreach ($x in $tests) {
  Write-Host "`n=== $($x.rule)  [$($x.t)-$($x.n)] ===" -ForegroundColor Cyan
  Invoke-AtomicTest $x.t -TestNumbers $x.n -GetPrereqs
  Invoke-AtomicTest $x.t -TestNumbers $x.n
}
"`nBITDI: $(Get-Date -Format HH:mm:ss)"
Write-Host "Indi ~6-7 deqiqe gozle, sonra Kibana -> Security -> Alerts (Last 15 min) yoxla." -ForegroundColor Yellow

# --- TEMIZLEME (alertleri yoxladiqdan SONRA isled) ---
# foreach ($x in $tests) { Invoke-AtomicTest $x.t -TestNumbers $x.n -Cleanup }

# --- DESTRUKTIV (istege bagli, snapshot var ik) ---
# Invoke-AtomicTest T1490     -TestNumbers 1 -GetPrereqs; Invoke-AtomicTest T1490     -TestNumbers 1   # vssadmin delete shadows
# Invoke-AtomicTest T1685.005 -TestNumbers 1                                                           # wevtutil clear logs
