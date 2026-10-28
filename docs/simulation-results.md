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
| T1562.001 (Defender) | `Set-MpPreference -DisableRealtimeMonitoring` | ✅ gəldi |
| T1047 (WMIC) | `wmic process call create` | ✅ gəldi |

Nəticə: qaydalar yalnız sənəddə yox, real detektorda işləyir.

## 2. Əsas tapıntı — WMIC hərfə həssaslıq boşluğu

Qaydanın komanda sətri uyğunlaşması əvvəlcə Elasticsearch `keyword` sahəsində
hərfə həssas idi. "Əvvəl ölç, sonra dəyiş" prinsipi ilə Kibana-da sübut edildi:

| Əmr | Hərf | Discover-də hadisə | Qaydanın sorğusu | Alert |
|---|---|---|---|---|
| `wmic process call create` | kiçik | var | tapır | ✅ var |
| `wmic Process Call Create` | qarışıq | var (1) | 0 tapır | ❌ yox |

İkinci sətir nəzarət testidir: qaydanın özü sağlamdır, problem yalnız hərf
böyüklüyündədir. Hücumçunun etməli olduğu tək şey böyük hərf yazmaqdır — detektor kor olur.

**Həll:** `convert.py` hərfə həssas olmayan uyğunlaşmaya keçirildi (regex simvol sinifləri /
EQL backend). Düzəlişdən sonra qarışıq hərfli əmr də alert verir. Bu, "əvvəl/sonra"
müqayisəsi kimi sənədləşdirilib.

## 3. İkinci tapıntı — Defender ASR real hücumu bloklayır

İki qaydanın positive testini **real hücum əmri** ilə yaratmağa çalışdıqda Windows
Defender-in Attack Surface Reduction (ASR) qaydası prosesi başlamağa qoymadı:

| Texnika | Real əmr | Nəticə |
|---|---|---|
| T1003.001 (LSASS dump) | `procdump -ma lsass.exe` | `Access is denied` — ASR blokladı |
| T1105 (certutil download) | `certutil -urlcache -f http://…` | `Access is denied` — ASR blokladı |

Bu, müdafiənin işlədiyini göstərir və əlavə bir müdafiə qatını təsdiqləyir.

Test faylları isə real hadisədən command_line dəyişdirilərək düzəldildi: qayda yalnız
`Image` və `command_line` sahələrini yoxladığı üçün bu, aşkarlama məntiqini tam yoxlayır,
amma LSASS dump edilmir / Defender söndürülmür.

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

## 5. Növbəti mərhələ

- Atomic Red Team ilə hər texnika üzrə tam, avtomatlaşdırılmış simulyasiya.
- Alert verməyən hər qaydanın səbəbinin bu sənədə əlavə edilməsi.
