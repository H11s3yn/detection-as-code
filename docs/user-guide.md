# İstifadə təlimatı

Sistem quraşdırılıb ([install-guide.md](install-guide.md)). Bu sənəd gündəlik işi izah edir: qayda yazmaq, yoxlatmaq, SIEM-ə çatdırmaq, alertlərə baxmaq, səhvi geri qaytarmaq. Üç rol üçün nəzərdə tutulub: qayda yazan, review verən (code owner) və SIEM-i izləyən analitik.

## Əsas fikir

SIEM-də heç nə əl ilə dəyişdirilmir. Hər dəyişiklik repo-da edilir, yoxlanır, təsdiqlənir və avtomatik yüklənir. Nəticədə hər qaydanın kim tərəfindən, nə vaxt və niyə dəyişdiyi görünür, səhv olarsa geri qaytarmaq mümkündür.

```text
branch → qayda + test → PR → quality gate → code owner təsdiqi → merge → avtomatik deploy (~40 saniyə) → Kibana
```

## 1. Yeni qayda əlavə etmək

**a) Branch aç** (ad [CONTRIBUTING.md](../CONTRIBUTING.md)-ə uyğun olsun):

```bash
git checkout main && git pull
git checkout -b rule/<ad>
```

**b) Qaydanı yaz:** `rules/<taktika>/<ad>.yml`. Bütün məcburi sahələr [metadata-standard.md](metadata-standard.md)-dədir. Minimal nümunə:

```yaml
title: Qısa və aydın ad
id: <uuidgen ilə yeni UUID>
status: experimental
description: Nəyi aşkarladığı.
author: Ad
date: '2026-11-28'          # dırnaqda
tags:
  - attack.discovery        # taktika
  - attack.t1033            # texnika
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    Image|endswith: '\whoami.exe'
  condition: selection
falsepositives:
  - Administratorların gündəlik istifadəsi   # boş olmamalıdır
level: low
```

**c) Test faylları:** `tests/<id>/positive.json` və `tests/<id>/negative.json`. Hər ikisi ECS formatında hadisə siyahısıdır.

- `positive.json`: qaydanın **tutmalı** olduğu hadisələr
- `negative.json`: oxşar, amma **tutmamalı** olduğu hadisələr (məsələn `net localgroup` qaydası `net group "Domain Admins"` üçündürsə)

Real nümunə üçün mövcud qaydalardan birinin test qovluğuna baxın. Hadisələri Kibana-dan və ya Sysmon-dan götürmək olar.

**d) Lokalda yoxla:**

```bash
pip install -r requirements.txt
sigma check rules/
python scripts/validate.py
python scripts/convert.py
```

**e) Push et və PR aç.** Hər qayda ayrı PR-da olmalıdır.

## 2. Quality gate: PR-da nə yoxlanır

PR açılanda avtomatik işləyir. Hamısı yaşıl olmasa merge mümkün deyil.

| # | Yoxlama | Nəyi tutur |
|---|---|---|
| 1 | `yamllint` | YAML formatı |
| 2 | `sigma check` | Sigma sintaksisi |
| 3 | `scripts/validate.py` | Çatışmayan metadata sahələri, səhv format, təkrar ID, test faylı yoxdur, ATT&CK-da olmayan teq |
| 4 | `scripts/convert.py` | Qaydanın EQL-ə çevrilə bilməsi |
| 5 | `scripts/run_tests.py` | `positive.json` tutulur, `negative.json` tutulmur (Elasticsearch-də real sorğu ilə) |
| 6 | `scripts/report.py` | ATT&CK əhatə hesabatı |

Qırmızı olarsa, Actions-dakı jurnalda hansı fayl və hansı səhv olduğu yazılır. Düzəldib eyni branch-a push edin, yoxlama yenidən işləyir. Nümunələr: [quality-gate.md](quality-gate.md).

## 3. Review və merge

- `rules/` üçün code owner təsdiqi məcburidir ([CODEOWNERS](../.github/CODEOWNERS)).
- Müəllif öz PR-ını təsdiqləyə bilməz.
- Merge üsulu: **Create a merge commit** (squash yox). Səbəb: `git revert -m 1` ilə geri qaytarmaq üçün merge commit lazımdır.
- Review siyahısı: [CONTRIBUTING.md](../CONTRIBUTING.md).

## 4. Deploy-u izləmək

Merge-dən sonra Actions → **Deploy** avtomatik başlayır (`rules/`, `scripts/` və ya `requirements.txt` dəyişibsə). Təxminən 40 saniyə sonra qayda SIEM-dədir.

Yoxlama: Kibana → Security → Rules → Detection rules, qayda `detection-as-code` teqi ilə görünür və `enabled`-dir.

Deploy 4 addımdan keçir (`scripts/deploy.py`):

1. **Kibana-nı gözləyir:** VM yenicə açılıbsa, hazır olana qədər (maksimum 5 dəqiqə).
2. **Tipi dəyişən qaydaları yenidən yaradır:** məsələn `query` → `eql`.
3. **Yükləyir:** eyni `rule_id` varsa yeniləyir, yoxdursa yaradır, təkrar işə salmaq zərərsizdir.
4. **Silinənləri təmizləyir:** repo-da olmayan, `detection-as-code` teqli qaydaları Kibana-dan silir.

Beləcə Kibana həmişə repo-nun güzgüsüdür.

## 5. Mövcud qaydanı dəyişmək

Eyni fayl üzərində dəyişiklik edin, `modified` tarixini yeniləyin, testləri uyğunlaşdırın, PR açın. **`id` dəyişmir**: Kibana qaydanı həmin `id` ilə tapıb yeniləyir. `id` dəyişsə köhnə qayda silinər, yenisi yaranar və tarixçə kəsilər.

## 6. Qaydanı silmək

Qayda faylını (və test qovluğunu) PR ilə silin. Merge-dən sonra deploy-un 4-cü addımı onu Kibana-dan da silir.

## 7. Alertlərə baxmaq

- **Alertlər:** Kibana → Security → Alerts. Hər alertdə qayda adı, host, istifadəçi, proses və səbəb görünür.
- **Severity:** qaydanın `level` sahəsindən gəlir (`low`/`medium`/`high`); `risk_score` `scripts/convert.py`-dakı cədvəldən təyin olunur.
- **Ümumi vəziyyət:** Kibana-da dashboard qurmaq tövsiyə olunur. Laboratoriyada "Detection-as-Code: İcmal" adlı dashboard hadisə sayını, host üzrə aktivliyi, `event.code` bölgüsünü və ən çox işləyən prosesləri göstərir (dashboard repo-da deyil, Kibana-dadır).
- **Sensor sağlamlığı:** Sysmon susdurulsa və ya log kəsilsə nə baş verir, hansı qayda siqnal verir: [sensor-health.md](sensor-health.md).

Qaydalar hər 5 dəqiqədən bir işləyir və son 6 dəqiqəyə baxır, ona görə hadisədən alertə qədər bir neçə dəqiqə gecikmə normaldır.

## 8. Səhv qayda canlıya çatdı: geri qaytarma

İki yol var, adətən ardıcıl istifadə olunur:

| Yol | Nə vaxt | Necə | Xüsusiyyət |
|---|---|---|---|
| **Sürətli** | SIEM-i dərhal bərpa etmək lazımdır | Actions → Deploy → Run workflow → `ref` = son yaxşı commit-in **tam** SHA-sı | Dərhal təsir edir, amma **müvəqqətidir**: git dəyişmir, növbəti deploy səhvi qaytarar |
| **Düzgün** | Daimi düzəliş | `git revert` PR-ı → gate → review → merge | Tarixçə qalır (force push yoxdur), ~40 saniyə |

Qısa SHA işləmir, 40 simvolluq tam SHA lazımdır. Addımlar və real zaman xətti: [rollback-demo.md](rollback-demo.md).

## 9. Təcili hal: review verən yoxdur

Aktiv hadisə zamanı yeni qayda lazımdırsa və review verə biləcək kimsə əlçatan deyilsə, sənədləşdirilmiş təcili yol var. Qaydaları, məhdudiyyətləri və səhər hesabatı: [emergency-deploy.md](emergency-deploy.md).

## 10. Aylıq: ATT&CK siyahısı

`attack-update.yml` hər ayın 1-i MITRE-dən texnika siyahısını yoxlayır. Fərq varsa özü PR açır. Bu PR-a baxın: silinən və ya adı dəyişən texnikanı işlədən qayda varsa, əvvəlcə onu düzəldin, sonra merge edin. Fərq yoxdursa PR açılmır.

## Qısa xatırlatma

| Nə etmək istəyirsiniz | Harada |
|---|---|
| Yeni qayda | `rules/<taktika>/` + `tests/<id>/` → PR |
| Qaydanı dəyişmək | Eyni fayl, `id` dəyişmir |
| Qaydanı silmək | Faylı sil → PR |
| Deploy-a baxmaq | Actions → Deploy |
| Alertlər | Kibana → Security → Alerts |
| Səhv canlıdadır | Bölmə 8 |
| Gecə, review yoxdur | Bölmə 9 |
