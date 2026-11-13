# Simulyasiya nəticələri

Bu sənəd qaydaların real Windows hadisələri ilə yoxlanmasının nəticələrini toplayır:
boru xəttinin canlı təsdiqi, aşkarlanan boşluqlar və onların həlli.

Mühit: VM2 (Windows Server 2022) → Sysmon → Winlogbeat → VM1 (Elasticsearch + Kibana).
Qaydalar GitHub-da saxlanılır, `convert.py` ilə Kibana detection qaydalarına çevrilir.

## 1. Boru xəttinin canlı təsdiqi

`PR → CI yoxlaması → merge → Kibana deploy → alert` zənciri insan əli dəymədən işləyir.
VM2-də işlədilən real əmrlər Kibana **Security → Alerts**-də alert yaratdı:

| Texnika | Əmr | Alert |
|---|---|---|
| T1136.001 (net user) | `net user DaCUser /add` | ✅ gəldi |
| T1562.001 (Defender)¹ | `Set-MpPreference -DisableRealtimeMonitoring` | ✅ gəldi |
| T1047 (WMIC) | `wmic process call create` | ✅ gəldi |

Nəticə: qaydalar yalnız sənəddə yox, real detektorda işləyir.

> ¹ ATT&CK v19 yenilənməsindən sonra (PR #58) Defender söndürmə qaydası repoda
> `attack.t1685`, wevtutil log silmə qaydası `attack.t1685.005` kimi teqlənib
> (`defense-impairment` taktikası). Köhnə nömrələr: T1562.001 və T1070.001.

## 2. Əsas tapıntı — WMIC hərfə həssaslıq boşluğu

Qaydanın komanda sətri uyğunlaşması əvvəlcə Elasticsearch `keyword` sahəsində
hərfə həssas idi. "Əvvəl ölç, sonra dəyiş" prinsipi ilə Kibana-da sübut edildi:

| Əmr | Hərf | Discover-də hadisə | Qaydanın sorğusu | Alert |
|---|---|---|---|---|
| `wmic process call create` | kiçik | var | tapır | ✅ var |
| `wmic Process Call Create` | qarışıq | var (1) | 0 tapır | ❌ yox |

İkinci sətir nəzarət testidir: qaydanın özü sağlamdır, problem yalnız hərf
böyüklüyündədir. Hücumçunun etməli olduğu tək şey böyük hərf yazmaqdır — detektor kor olur.

**Həll:** `convert.py` EQL backend-inə keçirildi (`like~` hərfə həssas olmayan operator).
Düzəlişdən sonra qarışıq hərfli `wmic Process Call Create` əmri də alert verdi —
Kibana Alerts-də canlı təsdiqləndi:

| Əmr | Backend | Alert |
|---|---|---|
| `wmic Process Call Create` | köhnə (hərfə həssas) | ❌ yox |
| `wmic Process Call Create` | EQL (`like~`) | ✅ var |

Eyni hücum, eyni qayda, eyni log yolu — yeganə dəyişən backend-dir.

## 3. İkinci tapıntı — Defender Antivirus real hücum əmrlərini bloklayır

Bəzi qaydaların positive testini **real hücum əmri** ilə yaratmağa çalışdıqda Windows
Defender prosesi başlamağa qoymadı (`Access is denied`):

| Texnika | Real əmr | Nəticə |
|---|---|---|
| T1003.001 (LSASS dump) | `procdump -ma lsass.exe` | `Access is denied` — Defender blokladı |
| T1105 (certutil download) | `certutil -urlcache -f http://…` | `Access is denied` — Defender blokladı |
| T1003.003 (ntdsutil IFM) | `ntdsutil … ifm …` | `Access is denied` — Defender blokladı |

Bu, müdafiənin işlədiyini göstərir və əlavə bir müdafiə qatını təsdiqləyir.

Test faylları isə real hadisənin strukturundan `command_line` (və lazım olanda `Image`)
dəyişdirilərək düzəldildi: qayda yalnız bu sahələri yoxladığı üçün bu, aşkarlama məntiqini
tam yoxlayır, amma LSASS dump edilmir / Defender söndürülmür / AD kopyalanmır.

> **Təkrar yoxlama (2026-11-09) — mexanizm təsbit olundu:** `Get-MpPreference` ASR qayda
> sayı **0**, AppLocker boş, WDAC söndürülü idi. Lakin canlı testdə `certutil -urlcache -f
> http://...` yenə **"Access is denied" ilə bloklandı**. Defender Operational jurnalı (Event
> **1116 / 1117**) səbəbi göstərdi: blok **Windows Defender Antivirus-un real-time qorumasıdır**
> — əmr sətri **`Trojan:Win32/Ceprolad.A`** imzası kimi tanınıb və proses **"Remove" əməli ilə
> açılışda dayandırılıb**. Yəni mexanizm ASR deyil, **Defender AV-nin command-line imza/davranış
> aşkarlamasıdır**. (procdump, ntdsutil, PsExec isə sadəcə quraşdırılmayıb — bloklanmır.)
> Nəticə: bu, əlavə müdafiə qatını təsdiqləyir; certutil prosesi ümumiyyətlə yaranmadığı üçün
> SIEM qaydası bu mühitdə tetiklənmir — positive test sintetik qalır (§4, §5).

## 4. Sintetik positive testlər

Bəzi texnikalar üçün real əmr destruktivdir və ya mühitdə mövcud deyil. Belə hallarda
positive test zərərsiz üsulla yaradıldı — qaydanın axtardığı command_line daşınır, amma
heç bir zərərli əməl icra olunmur:

| Texnika | Sintetik üsul |
|---|---|
| T1490 (vssadmin) | `delete shadows` əmri zərərsiz binarla — heç bir shadow copy silinmədi |
| T1204.002 (Office) | `WINWORD.EXE` adlı zərərsiz surət cmd.exe açdı |
| T1562.001 (Defender) | `Set-MpPreference` command-ı icra olunmadan loglandı |
| T1021.002 (PsExec) | Sysinternals aləti mühitdə yox — zərərsiz surət işlədildi |

Hər belə test PR təsvirində "sintetik" kimi qeyd olunub.

## 5. Hər qaydanın canlı alert statusu

Bütün 20 qayda `process_creation` (Sysmon Event ID 1) əsaslıdır — yəni qayda
prosesin `Image`, `CommandLine` və `ParentImage` sahələrinə baxır. Buna görə bir
qaydanın canlı alert verib-verməməsi əsasən **tetikləyici prosesin VM2-də ümumiyyətlə
yaranıb-yaranmamasından** asılıdır. Aşağıdakı cədvəl hər qaydanı bu məntiqlə qruplaşdırır.

Statuslar VM2 mühit profili ilə (aşağıda, 2026-11-09) həll olunub.

**İşarələr:**
- ✅ **təsdiqlənib** — Kibana Security → Alerts-də canlı alert görülüb
- ⬜ **alert gözlənilir** — tetikləyici binar VM2-də mövcuddur və proses yaranır; qalan tək addım VM1 Kibana-da canlı təsdiqdir
- ⚠️ **alert gözlənilir, positive sintetik qalır** — proses yaranır, amma real əmr destruktivdir və ya real əməl bloklana bilər, ona görə positive test sintetikdir
- ❌ **bu mühitdə təkrarlana bilməz** — tetikləyici binar yoxdur (Office / PsExec / ntdsutil) *və ya* binar var, amma açılışda bloklanır (certutil); positive test sintetik qalır

| # | Qayda | Texnika | Tetik (əsas sahə) | Status | Səbəb / qeyd |
|---|---|---|---|---|---|
| 1 | whoami | T1033 | `whoami.exe` | ✅ | Canlı təsdiqləndi |
| 2 | net user add | T1136.001 | `net.exe` + user + /add | ✅ | §1 canlı |
| 3 | Defender disable | T1685 *(köhnə T1562.001)* | powershell + `Set-MpPreference` + `-DisableRealtimeMonitoring` | ✅ | §1 canlı |
| 4 | WMIC proc create | T1047 | `wmic.exe` + process/call/create | ✅ | §1 canlı; EQL `like~` ilə hərf boşluğu bağlandı (§2) |
| 5 | systeminfo | T1082 | `systeminfo.exe` | ✅ | Atomic (T1082-1) → alert verdi (2026-11-13) |
| 6 | reg save SAM | T1003.002 | `reg.exe` + ` save ` + `hklm\sam` | ✅ | Atomic (T1003.002-1) → alert verdi (2026-11-13) |
| 7 | schtasks create | T1053.005 | `schtasks` + create | ✅ | Atomic (T1053.005-2) → alert verdi (2026-11-13) |
| 8 | sc create service | T1543.003 | `sc.exe` + create | ✅ | Atomic (T1543.003-2) → alert verdi (2026-11-13) |
| 9 | Run key persistence | T1547.001 | `reg add …\Run` | ✅ | Atomic (T1547.001-1) → alert verdi (2026-11-13) |
| 10 | bitsadmin download | T1105 | `bitsadmin` + transfer/addfile + http | ✅ | Atomic (T1105-9) → alert verdi (2026-11-13) |
| 11 | ps encoded cmd | T1059.001 | powershell + `-enc` | ⚠️ | Atomic (T1059.001-15) işlədi — `powershell.exe -NoProfile -E <b64>`, **amma alert VERMƏDİ**. Qayda `-enc`/`-EncodedCommand` axtarır, qısaldılmış **`-E`** formasını tutmur → **aşkarlama boşluğu** (WMIC hərf boşluğuna bənzər; qayda `-e`/`-ec`/`-enc` variasiyalarını əhatə etməlidir) |
| 12 | net group Domain Admins | T1069.002 | `net.exe` + group + "domain admins" | ✅ | Atomic (T1069.002-3) → alert verdi (2026-11-13) |
| 13 | nltest domain trusts | T1482 | `nltest.exe` + domain_trusts | ✅ | Atomic (T1482-2) → alert verdi (2026-11-13) |
| 14 | vssadmin delete shadows | T1490 | `vssadmin` + delete + shadows | ⚠️ | Real əmr **destruktiv** (shadow silir) → positive sintetik. Proses yaranarsa alert verər |
| 15 | wevtutil clear logs | T1685.005 *(köhnə T1070.001)* | `wevtutil` + ` cl ` | ⚠️ | Real əmr **destruktiv** (log silir) → positive sintetik. Proses yaranarsa alert verər |
| 16 | office spawn shell | T1204.002 | ParentImage winword/excel → cmd/powershell | ❌ | **Office quraşdırılmayıb (təsdiqləndi)** → valideyn-uşaq tetik yoxdur → sintetik surət (`WINWORD.EXE`) qalır |
| 17 | PsExec | T1021.002 | `psexec.exe` / `psexesvc.exe` | ✅ | Atomic (T1021.002-3) `-GetPrereqs` ilə PsExec-i endirdi → `PSEXESVC.exe` işlədi → **alert verdi (2026-11-13)**. Lab mühitində canlı təsdiqləndi |
| 18 | LSASS dump | T1003.001 | procdump+lsass / rundll32+comsvcs+MiniDump | ✅ | Atomic (T1003.001-2, comsvcs.dll) → `rundll32.exe` MiniDump işlədi → **alert verdi (2026-11-13)** |
| 19 | certutil download | T1105 | `certutil` + urlcache + http | ❌ | **Defender AV blokladı** (Event 1116/1117, `Trojan:Win32/Ceprolad.A`) — əmr açılışda "Remove" ilə dayandırıldı → proses yaranmır → alert yox (§3) |
| 20 | ntdsutil IFM | T1003.003 | `ntdsutil` + ifm | ❌ | **ntdsutil yoxdur (AD DS rolu yox, təsdiqləndi)** → proses yaranmır → sintetik qalır. Canlı yalnız Domain Controller-də |

**Qalıcı nəticə (2026-11-13 Atomic Red Team ilə təsdiqləndi):** **14 qayda canlı alert verdi** (✅) —
Kibana Security → Alerts-də **49 alert**. 1 qayda (⚠️ ps-enc) aşkarlama boşluğu göstərdi. 2 qayda
(⚠️ vssadmin, wevtutil) destruktiv olduğu üçün atomic dəstinə daxil edilmədi — positive sintetik qalır.
3 qayda (❌) bu mühitdə təkrarlana bilmir (Office yox, certutil Defender tərəfindən bloklanır, ntdsutil/AD DS yox).

> **Atomic Red Team nəticəsi (2026-11-13):** `scripts/run-atomics.ps1` ilə 15 atomic test VM2-də
> işlədildi (`pre-atomic` snapshot-dan sonra). Hadisələr Sysmon → Winlogbeat → Elastic yolu ilə axdı
> və detection qaydaları **49 alert** yaratdı. **Qayda üzrə alert sayı:** whoami 31 · PsExec 3 ·
> net group DA 2 · net user 2 · nltest 2 · bitsadmin 1 · reg SAM 1 · sc create 1 · schtasks 1 ·
> systeminfo 1 · LSASS dump 1 · run key 1 · WMIC 1 · Defender disable 1. **PsExec** bu dəfə işlədi
> (atomic `-GetPrereqs` aləti endirdi). **ps-enc** işlədi, amma qayda `-E` qısa formasını tutmadığı
> üçün **alert vermədi** — aşkarlama boşluğu (§5, sətir 11).

**VM2 mühit profili** (təsdiqləndi 2026-11-09, yalnız VM2-də PowerShell ilə — VM1 lazım olmadan):

| Parametr | Dəyər |
|---|---|
| Rol | Standalone server, WORKGROUP (domenə qoşulu deyil, DC deyil) |
| Microsoft Office | quraşdırılmayıb |
| procdump / PsExec / ntdsutil | mövcud deyil |
| Native alətlər (net, nltest, wmic, rundll32, certutil, bitsadmin, vssadmin, wevtutil, reg, schtasks, sc, systeminfo, powershell) | mövcud |
| Defender ASR aktiv qayda | 0 |

Bu profil §5 statuslarının səbəbidir: ❌ sətirlər tetikləyici binar/şərt olmadığı üçün sintetikdir;
qalan native qaydaların prosesi yaranır, ona görə canlı alert gözlənilir.

## 6. Növbəti mərhələ

- ✔ **Canlı təsdiq tamamlandı (2026-11-13):** Atomic Red Team ilə 14 qayda canlı alert verdi (49 alert).
- ✔ **Mühit profili tamamlandı** (2026-11-09) — ❌ sətirlərin səbəbi qəti təsbit olundu.
- ✔ **certutil blokunun mənbəyi tapıldı:** Defender Antivirus (`Trojan:Win32/Ceprolad.A`, Event 1116/1117) — ASR yox, AV imza aşkarlaması (§3).
- 🔧 **ps-enc aşkarlama boşluğu (yeni tapıntı):** T1059.001 qaydası `-enc`/`-EncodedCommand` tutur, amma qısaldılmış `-E`/`-e`/`-ec` formalarını tutmur. Qayda bu variasiyaları əhatə edəcək şəkildə genişləndirilməlidir (WMIC hərf boşluğu kimi).
- ❌ sətirlər (office, certutil, ntdsutil) uyğun mühitdə (Office host / Defender istisnası / Domain Controller) ayrıca yoxlanmalıdır.
- vssadmin və wevtutil (destruktiv) ayrıca, ehtiyatla canlı yoxlanıla bilər.
