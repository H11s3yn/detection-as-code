# Atomic Red Team — simulyasiya planı (Modul D)

Bu sənəd Detection-as-Code qaydalarının **Atomic Red Team (ART)** ilə avtomatlaşdırılmış
simulyasiyasını təsvir edir: hər qayda üçün hansı atomic testin işlədiləcəyi, mühit
məhdudiyyətləri və doğrulama addımları.

- **Mühit:** VM2 (Windows Server 2022, standalone). ART `C:\AtomicRedTeam`-də quraşdırılıb.
- **Snapshot:** `pre-atomic` — bütün testlərdən sonra bu snapshot-a qayıdılır.
- **Defender:** real-time qoruma bəzi atomics-i bloklayır (aşağıda qeyd olunub).

## 1. Quraşdırma (bir dəfə)

```powershell
# Administrator PowerShell, VM2
Add-MpPreference -ExclusionPath "C:\AtomicRedTeam"
Invoke-WebRequest 'https://raw.githubusercontent.com/redcanaryco/invoke-atomicredteam/master/install-atomicredteam.ps1' -OutFile "C:\AtomicRedTeam\install.ps1" -UseBasicParsing
. "C:\AtomicRedTeam\install.ps1"; Install-AtomicRedTeam -getAtomics -Force
Import-Module invoke-atomicredteam -Force
```
> Qeyd: install skripti birbaşa `IEX` ilə işlədiləndə Defender AMSI onu "malicious"
> kimi bloklayır; ona görə əvvəlcə istisna qovluğuna yüklənib **dot-source** ilə işlədilir.

## 2. Qayda → atomic test xəritəsi

| # | Qayda | ART testi | Admin | Qeyd |
|---|---|---|---|---|
| 1 | whoami | `T1033-8` | — | User Discovery - whoami |
| 2 | net user add | `T1136.001-4` | ✓ | Create a new user |
| 3 | Defender disable | `T1685-19` | ✓ | Set-MpPreference -DisableRealtimeMonitoring |
| 4 | wmic proc create | `T1047-5` | — | WMI Execute Local Process |
| 5 | systeminfo | `T1082-1` | — | System Information Discovery |
| 6 | reg save SAM | `T1003.002-1` | ✓ | Registry dump of SAM |
| 7 | schtasks create | `T1053.005-2` | — | Scheduled task Local |
| 8 | sc create service | `T1543.003-2` | ✓ | Service Installation CMD |
| 9 | run key | `T1547.001-1` | — | Reg Key Run |
| 10 | bitsadmin download | `T1105-9` | — | BITSAdmin BITS Download |
| 11 | ps encoded | `T1059.001-15` | — | -EncodedCommand (prereq lazımdır) |
| 12 | net group DA | `T1069.002-3` | — | net group (Domain) — standalone-da xəta verir, proses yaranır |
| 13 | nltest trusts | `T1482-2` | — | Discover domain trusts with nltest |
| 14 | LSASS dump | `T1003.001-2` | ✓ | comsvcs.dll MiniDump (rundll32) — procdump yox |
| 15 | PsExec | `T1021.002-3` | ✓ | Copy & Execute with PsExec (prereq alətı endirir) |
| — | vssadmin delete | `T1490-1` | ✓ | **DESTRUKTİV** (shadow silir) — ayrıca, ehtiyatla |
| — | wevtutil clear | `T1685.005-1` | ✓ | **DESTRUKTİV** (log silir) — ayrıca, ehtiyatla |
| — | office spawn | — | — | ❌ Office quraşdırılmayıb + uyğun atomic yoxdur |
| — | certutil download | `T1105-7` | — | ❌ Defender AV bloklayır (Trojan:Win32/Ceprolad.A) |
| — | ntdsutil IFM | `T1003.003-3` | ✓ | ❌ ntdsutil yox (AD DS rolu yoxdur) |

**15 test işlədiləndir** (1–15). 2 destruktiv test ayrıca işlədilir. 3 test bu mühitdə
işləmir (office/certutil/ntdsutil — səbəblər `simulation-results.md` §5-də).

## 3. İşlətmə (Faza 2 — VM1 açıq olmalıdır)

Hər test üç mərhələdən keçir: **prereq → run → cleanup**.

```powershell
# nümunə (bir test)
Invoke-AtomicTest T1033 -TestNumbers 8 -GetPrereqs   # lazım olan aləti endirir
Invoke-AtomicTest T1033 -TestNumbers 8               # hücumu işlədir → Sysmon loglayır
Invoke-AtomicTest T1033 -TestNumbers 8 -Cleanup      # yaratdığını silir
```

15 testi bir dəfəyə işlətmək üçün `run-atomics.ps1` skriptindən istifadə et.

## 4. Doğrulama (VM1)

1. Skripti işlət (BASLANDI vaxtını qeyd et).
2. **~6-7 dəqiqə gözlə** (qaydalar hər 5 dəq-dən bir son 6 dəq-yə baxır).
3. Kibana → **Security → Alerts** → "Last 15 minutes" → hansı qaydalar alert verdi.
4. Nəticəni `simulation-results.md` §5 cədvəlində ✅/❌ kimi işarələ.

## 5. Təmizləmə

- Hər testi `-Cleanup` ilə təmizlə (yuxarıda).
- Sonda VirtualBox-da **`pre-atomic` snapshot-a qayıt** — Defender, qeydlər və bütün
  dəyişikliklər ilkin vəziyyətə dönür.
