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
| 5 | systeminfo | T1082 | `systeminfo.exe` | ⬜ | Zərərsiz, işləyir — VM-də təsdiqlə |
| 6 | reg save SAM | T1003.002 | `reg.exe` + ` save ` + `hklm\sam` | ⬜ | Admin ilə işləyir — təsdiqlə |
| 7 | schtasks create | T1053.005 | `schtasks` + create | ⬜ | İşləyir — təsdiqlə |
| 8 | sc create service | T1543.003 | `sc.exe` + create | ⬜ | İşləyir — təsdiqlə |
| 9 | Run key persistence | T1547.001 | `reg add …\Run` | ⬜ | İşləyir — təsdiqlə |
| 10 | bitsadmin download | T1105 | `bitsadmin` + transfer/addfile + http | ⬜ | İşləyir — təsdiqlə |
| 11 | ps encoded cmd | T1059.001 | powershell + `-enc` | ⬜ | İşləyir — təsdiqlə |
| 12 | net group Domain Admins | T1069.002 | `net.exe` + group + "domain admins" | ⬜ | Standalone (WORKGROUP) → `/domain` əmri xəta verir, **amma `net.exe` prosesi command_line ilə yaranır** → alert gözlənilir |
| 13 | nltest domain trusts | T1482 | `nltest.exe` + domain_trusts | ⬜ | `nltest.exe` mövcud; standalone-da əmr xəta verir, proses yaranır → alert gözlənilir |
| 14 | vssadmin delete shadows | T1490 | `vssadmin` + delete + shadows | ⚠️ | Real əmr **destruktiv** (shadow silir) → positive sintetik. Proses yaranarsa alert verər |
| 15 | wevtutil clear logs | T1685.005 *(köhnə T1070.001)* | `wevtutil` + ` cl ` | ⚠️ | Real əmr **destruktiv** (log silir) → positive sintetik. Proses yaranarsa alert verər |
| 16 | office spawn shell | T1204.002 | ParentImage winword/excel → cmd/powershell | ❌ | **Office quraşdırılmayıb (təsdiqləndi)** → valideyn-uşaq tetik yoxdur → sintetik surət (`WINWORD.EXE`) qalır |
| 17 | PsExec | T1021.002 | `psexec.exe` / `psexesvc.exe` | ❌ | **PsExec yoxdur (təsdiqləndi)** → proses yaranmır → sintetik qalır. Canlı yalnız alət quraşdırılsa |
| 18 | LSASS dump | T1003.001 | procdump+lsass / rundll32+comsvcs+MiniDump | ⚠️ | procdump **yoxdur**, amma `rundll32`+comsvcs MiniDump yolu mövcuddur; ASR=0 → proses yaranır → alert mümkün. Real LSASS dump edilmir → positive sintetik qalır |
| 19 | certutil download | T1105 | `certutil` + urlcache + http | ❌ | **Defender AV blokladı** (Event 1116/1117, `Trojan:Win32/Ceprolad.A`) — əmr açılışda "Remove" ilə dayandırıldı → proses yaranmır → alert yox (§3) |
| 20 | ntdsutil IFM | T1003.003 | `ntdsutil` + ifm | ❌ | **ntdsutil yoxdur (AD DS rolu yox, təsdiqləndi)** → proses yaranmır → sintetik qalır. Canlı yalnız Domain Controller-də |

**Qalıcı nəticə:** 4 qayda canlı təsdiqlənib (✅). 9 qaydanın tetikləyici binarı mövcuddur
və proses yaranır — yalnız VM1 Kibana təsdiqi qalır (⬜). 3 qayda (⚠️) üçün alert gözlənilir,
amma real əmr destruktiv olduğu üçün positive test sintetik qalır (vssadmin, wevtutil, LSASS).
4 qayda (❌) bu mühitdə təkrarlana bilmir — Office / PsExec / ntdsutil yoxdur, certutil isə
açılışda bloklanır; hamısı sintetik qalır.

> **Qeyd:** 9 ⬜ qaydanın tetik əmrləri 2026-11-09 14:03-də VM2-də uğurla işlədi (proseslər
> yarandı), lakin VM1 o an bağlı olduğu üçün Kibana-da alert təsdiqlənə bilmədi. VM1 açılanda
> əmrlər **yenidən** işlədilib ~6 dəqiqə sonra yoxlanmalıdır (qaydalar yalnız son 6 dəqiqəyə baxır).

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

- **Mühit profili tamamlandı** (yuxarıda, 2026-11-09) — ❌ sətirlərin səbəbi qəti təsbit olundu.
- Qalan iş (VM1 lazımdır): §5-dəki 13 ⬜/⚠️ qayda VM2-də işlədilib Kibana-da canlı alert təsdiqlənsin.
- ❌ sətirlər (office, psexec, ntdsutil) bu laboratoriya mühitində sintetik olaraq qalır;
  canlı yoxlama yalnız uyğun mühitdə (Office quraşdırılmış host / Sysinternals / Domain Controller) mümkündür.
- ✔ **certutil blokunun mənbəyi tapıldı:** Defender Antivirus (`Trojan:Win32/Ceprolad.A`, Event 1116/1117) — ASR yox, AV imza aşkarlaması (§3). İstəsə eyni üsulla procdump/ntdsutil üçün də təsdiqlənə bilər.
- Atomic Red Team ilə hər texnika üzrə tam, avtomatlaşdırılmış simulyasiya.
