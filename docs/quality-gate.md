# Quality gate

Hər Pull Request-də GitHub Actions (`pr-check.yml`) avtomatik 4 yoxlama işlədir.
Biri qırmızı olarsa, qayda main-ə düşməməlidir.

| # | Yoxlama | Nəyi tutur | Niyə lazımdır |
|---|---|---|---|
| 1 | `sigma check rules/` | Sigma sintaksis və condition xətaları | Qayda çevrilə bilməyən YAML olmasın |
| 2 | `scripts/validate.py` | Çatışmayan sahələr (məs. level), səhv format, təkrar ID, boş fayl, test faylı yoxdur | 3 boş qayda review-dan keçmişdi; insan gözü bunu tutmadı |
| 3 | `scripts/convert.py` | Kibana sorğusuna çevrilmə xətaları | Deploy zamanı sürpriz olmasın |
| 4 | `scripts/run_tests.py` | Positive log tutulmur və ya negative log tutulur | Field mapping səhvləri və çox geniş qaydalar |

Addım 4 üçün hər dəfə müvəqqəti Elasticsearch 9.5.5 qalxır və iş bitəndə silinir.
Test nəticəsi `build/test-results.json` artifact kimi saxlanır.

## Yeni qayda əlavə edəndə
- Qayda: `rules/<tactic>/<qisa_ad>.yml`
- Testlər: `tests/<qayda-id>/positive.json` və `negative.json` (məcburidir)
- Tarix dırnaqda yazılır: `date: '2026-10-27'`

## main-in qorunması (addım 22)
main ruleset ilə qorunur və repo sahibi də qaydalardan keçir:
- quality-gate yaşıl olmalıdır;
- branch ən son main ilə yoxlanmış olmalıdır (Update branch);
- code owner təsdiqi məcburidir (CODEOWNERS).
Nəticə: yoxlamadan keçməyən qayda təsdiqlənmiş olsa belə merge oluna bilmir
(nümunə: schtasks qaydasının test faylları yox idi).

## Planlaşdırılıb
- ATT&CK teqlərinin real olduğunu yoxlama (addım 29)
- yamllint (addım 29)
- run_tests.py-nin EQL ilə işləməsi və qarışıq hərfli test (addım 28)
- report.py-nin CI-a qoşulması (addım 31)