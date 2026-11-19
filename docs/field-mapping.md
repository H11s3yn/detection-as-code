# Sahə xəritəsi: Sigma → ECS → Winlogbeat

Qaydalar Sigma sahə adları ilə yazılır (`Image`, `CommandLine`), Kibana isə Winlogbeat-in ECS sahələrində axtarır (`process.executable`, `process.command_line`). Bu çevirməni `scripts/convert.py` iki addımda edir: pySigma-nın `ecs_windows` pipeline-ı, sonra bizim `WINLOGBEAT_FIX` düzəlişi. Nəticə EQL sorğusudur.

## Bizim qaydalarda istifadə olunan sahələr

| Sigma sahəsi | `ecs_windows` nəticəsi | Kibana-ya gedən sahə | Sysmon mənbəyi | Qayda sayı |
|---|---|---|---|---|
| `Image` | `process.executable.caseless` | `process.executable` | Event 1, `Image` | 19 |
| `CommandLine` | `process.command_line` | `process.command_line` | Event 1, `CommandLine` | 15 |
| `ParentImage` | `process.parent.executable.caseless` | `process.parent.executable` | Event 1, `ParentImage` | 1 (`office_spawn_shell`) |
| `TargetObject` | `registry.path` | `registry.path` | Event 13, `TargetObject` | 1 (`run_key_persistence`) |
| `OriginalFileName` | `process.pe.original_file_name` | `process.pe.original_file_name` | Event 1, `OriginalFileName` | 19 (`run_key_persistence`-dən başqa hamısı) |

Qalan 20 qaydanın 19-u `process_creation` (Sysmon Event 1), biri `registry_set` (Sysmon Event 13) kateqoriyasındadır.

## Nümunə: whoami qaydası

```yaml
detection:
  selection:
    Image|endswith:
      - '\whoami.exe'
      - '\WHOAMI.EXE'
```

| Addım | Sorğu |
|---|---|
| Yalnız `ecs_windows` | `any where process.executable.caseless like~ ("*\\whoami.exe", "*\\WHOAMI.EXE")` |
| `ecs_windows` + `WINLOGBEAT_FIX` (bizdə) | `any where process.executable like~ ("*\\whoami.exe", "*\\WHOAMI.EXE")` |

## Niyə `WINLOGBEAT_FIX` lazımdır

`ecs_windows` Elastic Agent üçün yazılıb: `Image` və `ParentImage` kimi sahələri `.caseless` alt-sahəsinə çevirir. Elastic Agent indeksində bu alt-sahə var, **Winlogbeat indeksində yoxdur**. Düzəlişsiz sorğu mövcud olmayan sahədə axtarır və heç vaxt nəticə vermir: qaydalar 26 oktyabra qədər məhz bu səbəbdən alert vermirdi (PR #14).

`WINLOGBEAT_FIX` `ecs_windows`-dan sonra işləyir (`priority=100`) və üç sahəni adi adına qaytarır:

| `ecs_windows` | `WINLOGBEAT_FIX`-dən sonra |
|---|---|
| `process.executable.caseless` | `process.executable` |
| `process.parent.executable.caseless` | `process.parent.executable` |
| `process.parent.name.caseless` | `process.parent.name` |

## Hərf böyüklüyü

`.caseless` alt-sahəsi Elastic Agent-də məhz hərfə baxmamaq üçündür. Onu çıxaranda adi `keyword` sahəsi qalır və Lucene sorğusu hərfə həssas olur: `wmic Process Call Create` tutulmurdu. EQL-ə keçid (PR #41) bunu həll etdi: `like~` və `:` operatorları hərfə baxmır.

Qaydalarda böyük hərf variantları (`\WHOAMI.EXE`, `'PROCESS'` və s.) hərfə həssas Lucene dövründən qalıb. EQL-də artıqdır, amma zərəri yoxdur. Onların təmizlənməsi planlaşdırılıb (`chore/simplify-rules`).

## Adı dəyişdirilmiş fayllar (`OriginalFileName`)

Hücumçu `whoami.exe`-ni `svchelper.exe` kimi kopyalayıb işə salsa, `Image` yoxlaması onu görmür. Exe faylının içində (PE başlığında) isə orijinal ad yazılıb və fayl adı dəyişəndə o dəyişmir. Sysmon bu adı `OriginalFileName` sahəsində göndərir.

Ona görə `process_creation` qaydalarında `Image` seçiminin yanında `OriginalFileName` seçimi də var:

```yaml
  selection_img:
    Image|endswith: '\whoami.exe'
  selection_orig:
    OriginalFileName: 'whoami.exe'
  condition: selection_img or selection_orig
```

Bəzi Windows alətlərində orijinal ad fayl adından fərqlidir: `systeminfo.exe` → `sysinfo.exe`, `nltest.exe` → `nltestRK.exe`, `PsExec.exe` → `psexec.c`, `pwsh.exe` → `pwsh.dll`. EQL-də `:` hərfə baxmır, ona görə `PowerShell.EXE` kimi yazılışlar da tutulur.

Hər qaydanın `positive.json` testində adı `svchelper.exe` olaraq dəyişdirilmiş bir hadisə var: qayda onu yalnız `OriginalFileName` vasitəsilə tuta bilər.

## Winlogbeat tərəfi

ECS sahələrini Winlogbeat özü yox, Elasticsearch-dəki ingest pipeline yaradır. Bunun üçün `winlogbeat.yml`-də bu sətir mütləqdir:

```yaml
pipeline: "winlogbeat-%{[agent.version]}-routing"
```

Bu sətir olmadan hadisələr yalnız `winlog.event_data.Image`, `winlog.event_data.CommandLine` kimi xam sahələrlə gəlir və heç bir qayda işləmir. Yoxlama: Kibana → Discover → `event.code : 1` → `process.executable` sahəsi görünməlidir (bax: `setup.md`, C4).

## Yeni sahə əlavə edəndə

1. Sahəni Sigma adı ilə yazın.
2. Çevrilmiş sorğunu yoxlayın:

   ```bash
   python -c "import sys; sys.path.insert(0,'scripts'); from convert import to_query; print(to_query('rules/<taktika>/<qayda>.yml'))"
   ```

3. Sorğuda `.caseless` qalıbsa, sahəni `WINLOGBEAT_FIX`-ə əlavə edin.
4. Sahənin Winlogbeat indeksində olduğunu Discover-də yoxlayın.
5. `positive.json` və `negative.json` testlərində həmin ECS sahəsindən istifadə edin.

## Bilinən məhdudiyyət

Sorğular `any where` ilə başlayır: `ecs_windows` Sigma `logsource` kateqoriyasını sorğuya filtr kimi əlavə etmir. Qayda `process.executable` sahəsi olan istənilən hadisəyə, məsələn Sysmon şəbəkə hadisəsinə (Event 3) də uyğun gələ bilər. İndiki 20 qayda üçün bu, praktik problem yaratmayıb.
