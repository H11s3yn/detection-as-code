# Rollback demosu (addım 24 və 30)

3 noyabr 2026-da canlı demoda səhv qayda dəyişikliyi main-ə merge olundu, 40 saniyəyə SIEM-ə çatdı və iki yolla geri qaytarıldı: əvvəl təcili deploy ilə, sonra `git revert` ilə. Bütün addımlar videoya yazıldı. Saatlar Bakı vaxtıdır (UTC+4).

## Ssenari

[PR #57](https://github.com/H11s3yn/detection-as-code/pull/57) whoami qaydasının statusunu `test` → `experimental` edir. `convert.py` yalnız `test` və `stable` qaydaları aktiv yükləyir (`"enabled": m["status"] in ("test", "stable")`), ona görə merge-dən sonra qayda Kibana-da söndürülür və whoami hücumu görünməz olur.

Bu səhvi quality gate tutmur: qaydanın məntiqi dəyişmir, sintaksis, metadata, çevrilmə və testlər keçir. Onu yalnız insan review-u tuta bilər. PR-ı Miri və Mahir təsdiqləmişdi, çünki o, əvvəlcədən razılaşdırılmış demo idi.

## Zaman xətti

| Saat | Hadisə | Sübut |
|---|---|---|
| 18:33:04 | PR #57 merge olundu (merge commit `5624789`) | [PR #57](https://github.com/H11s3yn/detection-as-code/pull/57) |
| 18:33:08 – 18:33:48 | Deploy #34: qayda `enabled: false` yükləndi | [run](https://github.com/H11s3yn/detection-as-code/actions/runs/41654800756) |
| ~18:38 | Sürətli rollback, 1-ci cəhd: ref = `7417ab6` (qısa kod), checkout uğursuz oldu | aşağıda |
| 18:44:04 – 18:44:38 | Deploy #36: ref = tam SHA, qayda `enabled: true` | [run](https://github.com/H11s3yn/detection-as-code/actions/runs/41656596403) |
| 18:57:42 | Revert PR #63 açıldı | [PR #63](https://github.com/H11s3yn/detection-as-code/pull/63) |
| 18:57:46 – 18:59:10 | Quality gate (PR yoxlaması #105) yaşıl | [run](https://github.com/H11s3yn/detection-as-code/actions/runs/41658888375) |
| 19:02:28 | Miri (code owner) təsdiqlədi | PR #63 |
| 19:03:47 | PR #63 merge olundu (`c3e6ad5`) | PR #63 |
| 19:03:51 – 19:04:25 | Deploy #37: main və SIEM eyni vəziyyətdə, qayda aktiv | [run](https://github.com/H11s3yn/detection-as-code/actions/runs/41659939394) |

Merge-dən SIEM-ə qədər: 44 saniyə (#57), 38 saniyə (#63).

## Yol 1: sürətli rollback (təcili hal)

**Actions → Deploy → Run workflow**, `ref` sahəsinə son yaxşı commit-in **tam** SHA-sı:

```text
7417ab6f9824f7b91b17e4720a1d2ff2ca0d971f
```

Son yaxşı commit-i tapmaq üçün: Deploy siyahısında səhvdən əvvəlki son yaşıl run (bizdə Deploy #33, commit `7417ab6`) → commit linki → səhifədəki kopyala düyməsi. Və ya:

```bash
git rev-parse 7417ab6
```

Yoxlama (VM1):

```bash
curl -s -u elastic "http://localhost:5601/api/detection_engine/rules?rule_id=456872f3-ea5f-4fb9-a18c-11b00361d6e7" | jq '{name, type, enabled}'
```

**Diqqət:** qısa kod (`7417ab6`) işləmir. `actions/checkout` onu branch və ya tag adı kimi axtarır (`refs/heads/7417ab6*`) və `git fetch ... failed with exit code 1` verir. İlk cəhddə məhz bu baş verdi.

**Məhdudiyyət:** git dəyişmir. main-də səhv qalır, növbəti deploy qaydanı yenə söndürər. Bu yol yalnız SIEM-i dərhal bərpa etmək üçündür, ardınca mütləq Yol 2 gəlir.

## Yol 2: git revert (düzgün yol)

```bash
git checkout main && git pull
git log --merges --grep="#57" -1 --oneline
git checkout -b fix/revert-whoami-experimental
git revert -m 1 --no-edit $(git log --merges --grep="#57" -1 --format=%H)
git push -u origin fix/revert-whoami-experimental
```

`-m 1` merge commit-i main tərəfinə görə geri alır. Bunun üçün səhv PR **"Create a merge commit"** üsulu ilə merge olunmalıdır.

Revert adi dəyişiklik kimi PR → quality gate → code owner təsdiqi → merge yolunu keçir. Müəllif öz PR-ını təsdiqləyə bilmir, `rules/` üçün təsdiqi Miri və ya Mahir verir. Force push ruleset-də bloklandığı üçün tarixçə yenidən yazılmır: həm səhv, həm düzəliş görünür.

```text
c3e6ad5 Merge pull request #63 from H11s3yn/fix/revert-whoami-experimental
9a6a4c8 Revert "Merge pull request #57 from H11s3yn/demo/whoami-experimental"
5624789 Merge pull request #57 from H11s3yn/demo/whoami-experimental
7417ab6 Merge pull request #55 from H11s3yn/fix/deploy-type-change
```

## Nəticələr

- Səhv dəyişiklik 44 saniyəyə SIEM-ə çatır, deməli düzəliş də eyni sürətlə çatır. Avtomatik deploy hər iki istiqamətdə işləyir.
- Status dəyişikliyi kimi "məntiqi" səhvləri gate tutmur. Code owner review-u əlavə bir formallıq deyil, müdafiə qatıdır.
- Səhv merge-dən 11.5 dəqiqə sonra SIEM sürətli rollback ilə bərpa olundu (qısa SHA xətası daxil). Revert PR açılandan merge-ə qədər 6 dəqiqə keçdi: gate 1.5 dəqiqə, qalanı review gözləməsi. İki yol bir-birini əvəz etmir, ardıcıl işlədilir.
- Rollback-dan sonra main və Kibana yenidən uyğundur: whoami `status: test`, `enabled: true`.
