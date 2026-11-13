# detection-as-code

Sigma qaydalarını kod kimi idarə edən Detection-as-Code layihəsi. Hər qayda GitHub-da saxlanılır, Pull Request-də avtomatik yoxlanılır, test olunur və `main`-ə merge olunandan sonra insan əli dəymədən Elastic SIEM-ə (Kibana Security) yüklənir.

```text
Sigma qaydası (YAML) → Pull Request → quality gate (CI) → review → merge
      → convert.py (Sigma → EQL) → deploy.py → Kibana detection qaydası → alert
```

## Nəticələr bir baxışda

- **20 Sigma qaydası**, 8 ATT&CK taktikası, hər qayda üçün `positive.json` və `negative.json` testi
- **Quality gate** hər PR-da 6 yoxlama aparır; səhv qayda `main`-ə düşə bilmir
- Merge-dən SIEM-ə qədər **~40 saniyə** ([rollback demosu](docs/rollback-demo.md))
- Atomic Red Team simulyasiyası: **14 qayda canlı alert verdi, Kibana-da 49 alert** ([nəticələr](docs/simulation-results.md))
- Simulyasiya iki aşkarlama boşluğu tapdı və hər ikisi bağlandı:
  - WMIC əmrinin hərf böyüklüyü ilə yayınması: EQL backend-inə (`like~`) keçidlə həll olundu
  - PowerShell `-E` qısaltması ilə `ps_encoded_command`-dan yayınma: qaydaya `-e`, `-ec`, `-en` formaları əlavə olundu

## Komanda

| Üzv | Modul | Məsuliyyət |
|---|---|---|
| Hüseyn (kapitan) | C | SIEM, `convert.py`, deploy, rollback |
| Elmir | B | CI, quality gate, yamllint, ATT&CK yoxlaması |
| Miri | A | Repo strukturu, metadata standartı, Sigma qaydaları, review |
| Mahir | D | Windows VM, test logları, simulyasiya, hesabat |

## Repo strukturu

```text
rules/<taktika>/<qayda>.yml     Sigma qaydaları
tests/<qayda-id>/               positive.json və negative.json test logları
schema/                         metadata JSON sxemi, ATT&CK taktika/texnika siyahıları
scripts/
  validate.py                   metadata, unikal ID, ATT&CK teqləri, test fayllarının yoxlanması
  convert.py                    Sigma → EQL → Kibana detection qaydası (build/rules.ndjson)
  run_tests.py                  testləri Elasticsearch-də qaydanın sorğusu ilə yoxlayır
  report.py                     ATT&CK coverage hesabatı və Navigator layer (reports/)
  deploy.py                     qaydaları Kibana-ya yükləyir
  run-atomics.ps1               Atomic Red Team testlərini VM2-də işlədir
siem/                           Elasticsearch + Kibana (Docker Compose)
docs/                           sənədlər (aşağıda)
.github/workflows/
  pr-check.yml                  hər PR üçün quality gate
  deploy.yml                    main-ə merge olunanda SIEM-ə deploy (self-hosted runner)
```

## Qaydalar

| Taktika | Qayda | ATT&CK | Səviyyə |
|---|---|---|---|
| Execution | `ps_encoded_command` | T1059.001 | medium |
| Execution | `wmic_process_call_create` | T1047 | medium |
| Execution | `office_spawn_shell` | T1204.002 | high |
| Persistence | `net_user_add` | T1136.001 | high |
| Persistence | `run_key_persistence` | T1547.001 | medium |
| Persistence | `sc_create_service` | T1543.003 | medium |
| Persistence | `schtasks_create` | T1053.005 | medium |
| Credential Access | `lsass_dump` | T1003.001 | high |
| Credential Access | `reg_save_sam` | T1003.002 | high |
| Credential Access | `ntdsutil_ifm` | T1003.003 | high |
| Defense Evasion | `defender_disable_realtime` | T1685 | high |
| Defense Evasion | `wevtutil_clear_logs` | T1685.005 | high |
| Discovery | `whoami_execution` | T1033 | low |
| Discovery | `systeminfo_execution` | T1082 | low |
| Discovery | `nltest_domain_trusts` | T1482 | medium |
| Discovery | `net_group_domain_admins` | T1069.002 | medium |
| Lateral Movement | `psexec_execution` | T1021.002 | high |
| Command and Control | `certutil_download` | T1105 | high |
| Command and Control | `bitsadmin_download` | T1105 | medium |
| Impact | `vssadmin_delete_shadows` | T1490 | high |

Bütün qaydalar Sysmon Event ID 1 (`process_creation`) əsaslıdır. Hər qaydanın canlı alert statusu: [docs/simulation-results.md](docs/simulation-results.md).

## Quality gate

`pr-check.yml` hər Pull Request-də bu addımları işlədir. Biri uğursuz olsa, PR merge oluna bilməz:

0. `yamllint rules/`: YAML stili
1. `sigma check rules/`: Sigma sintaksisi
2. `validate.py`: məcburi metadata, unikal UUID, düzgün ATT&CK teqləri, test fayllarının mövcudluğu
3. `convert.py`: qayda EQL-ə çevrilə bilir
4. `run_tests.py`: positive test alert verir, negative test vermir
5. `report.py`: ATT&CK coverage hesabatı (test nəticələri və hesabat artefakt kimi saxlanılır)

`main` qorunur: birbaşa push qadağandır, ən azı 1 təsdiq və yaşıl quality gate tələb olunur. Ətraflı: [docs/quality-gate.md](docs/quality-gate.md).

## Tez başlanğıc

```bash
git clone https://github.com/H11s3yn/detection-as-code.git
cd detection-as-code
pip install -r requirements.txt

sigma check rules/
python scripts/validate.py
python scripts/convert.py          # build/rules.ndjson
python scripts/run_tests.py        # Elasticsearch lazımdır (ES_URL, default localhost:9200)
python scripts/report.py           # reports/index.html
```

Sıfırdan bütün mühiti (VM1 SIEM, VM2 Windows + Sysmon + Winlogbeat, GitHub runner) qurmaq üçün: [docs/setup.md](docs/setup.md).

## Yeni qayda əlavə etmək

1. `main`-dən yeni branch aç: `git checkout -b rule/<ad> origin/main`
2. `rules/<taktika>/<ad>.yml` yaz ([metadata standartı](docs/metadata-standard.md))
3. `tests/<id>/positive.json` və `negative.json` əlavə et
4. Lokalda `sigma check` və `python scripts/validate.py` işlət
5. Push et, PR aç, quality gate yaşıl olsun, review gözlə

Branch adları, commit formatı və review siyahısı: [CONTRIBUTING.md](CONTRIBUTING.md).

## Rollback

Səhv qayda SIEM-ə çatarsa iki yol var:

- **Sürətli:** Actions → Deploy → Run workflow, `ref` sahəsinə son yaxşı commit-in tam SHA-sı
- **Düzgün:** `git revert` PR-ı açılır, quality gate və review-dan keçib merge olunur, deploy avtomatik işləyir

Canlı demo və zaman xətti: [docs/rollback-demo.md](docs/rollback-demo.md).

## Sənədlər

| Sənəd | Məzmun |
|---|---|
| [setup.md](docs/setup.md) | Sıfırdan quraşdırma təlimatı |
| [metadata-standard.md](docs/metadata-standard.md) | Qayda metadata standartı |
| [quality-gate.md](docs/quality-gate.md) | CI yoxlamaları və rədd edilən PR nümunələri |
| [field-mapping.md](docs/field-mapping.md) | Sigma → ECS → Winlogbeat sahə xəritəsi |
| [simulation-results.md](docs/simulation-results.md) | Canlı simulyasiya nəticələri və tapılan boşluqlar |
| [atomic-red-team-plan.md](docs/atomic-red-team-plan.md) | Atomic Red Team simulyasiya planı |
| [rollback-demo.md](docs/rollback-demo.md) | Rollback demosu |
| [splunk.md](docs/splunk.md) | Bonus: eyni qaydaların Splunk-a çevrilməsi |

## Məhdudiyyətlər

- `certutil_download` canlı yoxlana bilmədi: Defender Antivirus əmri açılışda bloklayır.
- `ntdsutil_ifm` yalnız Domain Controller-də işləyir, `office_spawn_shell` Office tələb edir. Bu qaydaların positive testləri sintetikdir.
- `vssadmin_delete_shadows` və `wevtutil_clear_logs` destruktiv olduğu üçün sintetik testlə yoxlanılıb.
