# Təcili yol: review verən yoxdur

Normal axında qayda SIEM-ə yalnız PR, quality gate və code owner təsdiqindən sonra çatır. Bəzən bu təsdiq gözlənilə bilmir: gecədir, hamı yatıb, amma aktiv hadisə var və dərhal yeni qayda lazımdır. Bu sənəd həmin vəziyyət üçün qapını, onun necə işlədiyini və istifadə edəndən nə tələb olunduğunu izah edir.

## Əsas prinsip

**`main` heç vaxt review-suz dəyişmir.** Ruleset-in bypass siyahısı boşdur: nə admin, nə də başqası təsdiqsiz `main`-ə yaza bilər. Təcili yol `main`-i keçmir. O, qaydanı yalnız **SIEM-ə birbaşa yükləyir** və bu yükləmə müvəqqətidir. Qayda daimi olmaq üçün sonradan adi yoldan (review + merge) keçməlidir.

## Qapı nədir

`Deploy` workflow-u (`.github/workflows/deploy.yml`) əl ilə işə salına bilər (`workflow_dispatch`) və `ref` sahəsi qəbul edir: istənilən commit, tag və ya branch. Adi halda deploy yalnız `main`-dən gedir, bu halda isə hələ merge olunmamış branch-dan da getməsi mümkündür.

## Nə vaxt istifadə olunur

Yalnız bütün şərtlər birlikdə ödənəndə:

1. Aktiv hadisə və ya dərhal bağlanmalı aşkarlama boşluğu var.
2. Review verə biləcək code owner əlçatan deyil (zəng və mesaj cəhdi edilib).
3. Gözləmək riski qaydanı review-suz yükləmək riskindən böyükdür.

Adi iş, tələsən iş və ya "sabaha qədər gözləmək istəmirəm" bu yolun səbəbi deyil.

## Addımlar

1. **Branch və qayda.** Adi qaydada: `rule/<ad>` branch-ı, qayda faylı, `positive.json` və `negative.json`.
2. **PR aç və gate-i gözlə.** PR açılanda quality gate GitHub-un öz maşınında işləyir. **Gate yaşıl olmayınca davam etmə.** Təcili yolun deploy addımı gate-i yenidən işlətmir, ona görə yoxlama yalnız PR-dakı nəticədir.
3. **Deploy et.** Actions → **Deploy** → Run workflow. "Use workflow from" = `main`, `ref` = branch adı və ya commit-in **tam** SHA-sı (qısa kod işləmir).
4. **Yoxla.** Kibana → Security → Rules → Detection rules: qayda `enabled`-dir. Sonra hadisəni yenidən yarat və alertin gəldiyini gör.
5. **Qeyd et.** PR təsvirinin əvvəlinə yaz: `TƏCİLİ DEPLOY`, səbəb (bir cümlə), vaxt, kim işə saldı.
6. **Səhər:** PR-ı code owner-ə göndər. Review verilib merge olunanda qayda daimi olur.

## Nə izsiz qalmır

| Nə | Harada görünür |
|---|---|
| Kim, nə vaxt, hansı `ref` ilə deploy etdi | Actions → Deploy run-ı |
| Hansı qayda və hansı dəyişiklik | PR və commit-lər |
| Gate nəticəsi | PR-dakı `quality-gate` yoxlaması |
| Niyə təcili idi | PR təsvirindəki qeyd |

Beləcə təcili istifadə "sənəd kimi qalır": hər dəfə izlənə bilən iz buraxır.

## Müvəqqətilik: öz-özünə təmizlənmə

`deploy.py`-nin sonuncu addımı repo-da olmayan, `detection-as-code` teqli qaydaları Kibana-dan silir. Deməli, təcili yüklənmiş qayda `main`-ə merge olunmasa, **növbəti normal deploy zamanı SIEM-dən silinəcək**. Bu, silmə məntiqinin yan təsiridir, amma faydalıdır: review-dan keçməyən qayda daimi qala bilmir.

Bunun nəticəsi: səhər PR-ı unutmaq təkcə intizam pozuntusu deyil, qaydanın itməsi deməkdir. Bu səbəbdən təcili yolu istifadə edən sabahı gözləməlidir.

## Hesabat (istifadə edənin məsuliyyəti)

Təcili yolu işlədən şəxs səhər komandaya qısa hesabat verir:

```text
Təcili deploy hesabatı
Nə vaxt:      <tarix və saat>
Kim:          <ad>
Nə:           <qayda adı, PR linki>
Niyə:         <hadisənin qısa təsviri>
Review niyə yox idi: <kimə zəng edildi, niyə əlçatan deyildi>
Gate nəticəsi: <yaşıl / run linki>
Yoxlama:      <alert gəldimi>
Növbəti addım: <review kimdə, nə vaxta qədər merge>
```

## Məhdudiyyətlər (dürüst qeyd)

Bu yol indi **prosesə və etibara** əsaslanır, texniki məcburiyyətə yox:

- Deploy-u repo-ya yazma icazəsi olan hər kəs işə sala bilər.
- "Səbəb" sahəsi məcburi deyil, qeyd əl ilə yazılır.
- Səhər hesabatı və review-nun verilməsi avtomatik tələb olunmur.
- Deploy addımı gate-i təkrar işlətmir.

Kiçik komandada və laboratoriyada bu kifayətdir. Real mühitdə bu boşluqların necə bağlanması [production-guide.md, 3-cü bölmə](production-guide.md#3-təcili-yol-və-gecə-əhatəsi)-də izah olunub.
