# Quality gate

Hər Pull Request-də GitHub Actions (`pr-check.yml`) avtomatik 6 yoxlama işlədir.
Biri qırmızı olarsa, qayda main-ə düşə bilməz.

| # | Yoxlama | Nəyi tutur | Niyə lazımdır |
|---|---|---|---|
| 0 | `yamllint rules/` | Girinti, YAML sintaksisi, təkrar açarlar | YAML səhvi sonrakı addımlara çatmasın |
| 1 | `sigma check rules/` | Sigma sintaksis və condition xətaları | Qayda çevrilə bilməyən YAML olmasın |
| 2 | `scripts/validate.py` | Çatışmayan sahələr (məs. level), səhv format, təkrar ID, boş fayl, test faylı yoxdur, ATT&CK v19-da olmayan teq | 3 boş qayda review-dan keçmişdi; insan gözü bunu tutmadı |
| 3 | `scripts/convert.py` | Kibana sorğusuna çevrilmə xətaları | Deploy zamanı sürpriz olmasın |
| 4 | `scripts/run_tests.py` | Positive log tutulmur və ya negative log tutulur | Field mapping səhvləri və çox geniş qaydalar |
| 5 | `scripts/report.py` | Hesabat yaradılır | Nəticələr artifact kimi saxlanır |

Addım 4 üçün hər dəfə müvəqqəti Elasticsearch 9.5.5 qalxır və iş bitəndə silinir.
Test nəticəsi `build/test-results.json` artifact kimi saxlanır.

## Yeni qayda əlavə edəndə
- Qayda: `rules/<tactic>/<qisa_ad>.yml`
- Testlər: `tests/<qayda-id>/positive.json` və `negative.json` (məcburidir)
- Tarix dırnaqda yazılır: `date: '2026-10-27'`
- ATT&CK teqləri v19-a uyğun olmalıdır (məs. `attack.defense-impairment`, `attack.t1685`)

## ATT&CK yoxlaması
`validate.py` hər `attack.*` teqini `schema/attack_techniques.txt` (706 texnika)
və `schema/attack_tactics.txt` (15 taktika) siyahıları ilə müqayisə edir.
`ATTACK_STRICT = True` olduğu üçün siyahıda olmayan teq CI-ı qırmızı edir.

Siyahını yeniləmək (MITRE yeni versiya çıxaranda):
1. `enterprise-attack.json` faylını MITRE-nin GitHub-ından yüklə
2. `python scripts/extract_attack.py <yol>/enterprise-attack.json`
3. Dəyişən iki `.txt` faylını commit et

## yamllint konfiqurasiyası
`.yamllint` yumşaldılıb ki, mövcud qaydalar dəyişdirilməsin:
- sətir uzunluğu 200-ə qədər (təsvir sətirləri uzundur);
- fayl sonunda boş sətir tələb olunmur;
- `new-lines: platform` — Windows-da CRLF xətası verməsin.

## main-in qorunması (addım 22)
main ruleset ilə qorunur və repo sahibi də qaydalardan keçir:
- quality-gate yaşıl olmalıdır;
- branch ən son main ilə yoxlanmış olmalıdır (Update branch);
- code owner təsdiqi məcburidir (CODEOWNERS).
Nəticə: yoxlamadan keçməyən qayda təsdiqlənmiş olsa belə merge oluna bilmir
(nümunə: schtasks qaydasının test faylları yox idi).

## Rədd edilən PR nümunələri (addım 23)
| Demo | Hansı yoxlama tutdu | Xəta |
|---|---|---|
| `test/no-level` | 2. validate.py | `'level' is a required property` |
| `test/no-tests` | 2. validate.py | `tests/<id>/positive.json yoxdur` |
| `test/duplicate-id` | 2. validate.py | `ID təkrarlanır` |
| `test/too-broad` | 4. run_tests.py | `❌ whoami_execution negative nəticə: 1` |

## Planlaşdırılıb
- run_tests.py-nin EQL ilə işləməsi və qarışıq hərfli test (addım 28)