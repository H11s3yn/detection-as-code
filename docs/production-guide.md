# Real mühitə keçid təlimatı

Bu repo **kurs layihəsi kimi laboratoriyada** qurulub və sınaqdan keçib: qaydaların yoxlanması, SIEM-ə avtomatik yüklənməsi, geri qaytarma və canlı hücum simulyasiyası işləyir. Real mühit (istehsalat) üçün isə laboratoriyada qəsdən sadə saxlanmış hissələr sərtləşdirilməli, bir neçə şey əlavə olunmalıdır. Bu sənəd hər birini üç sualla izah edir:

- **Niyə:** hansı problem və ya prinsipə əsasən lazımdır
- **Necə:** hansı addımlarla qurulur
- **Yoxlama:** düzgün qurulduğunu necə bilirik

Bu repo-nun özündə olan boşluqlar da [install-guide.md](install-guide.md#bu-təlimat-nəyi-əhatə-etmir) və [setup.md, Bilinən məhdudiyyətlər](setup.md) bölməsində qeyd olunub. Aşağıdakılar həmin məhdudiyyətlərin həllidir.

## Prioritet

| Mərhələ | Maddələr | Məqsəd |
|---|---|---|
| **P1:** istehsaldan əvvəl məcburi | 2 (təhlükəsizlik), 3 (təcili yolun qaydası), 4 (staging), 5 (alert marşrutu) | Sistem təhlükəsiz işləsin, alert kimsəyə çatsın |
| **P2:** ilk 1–2 ay | 3 (texniki sərtləşdirmə), 6 (tuning), 8 (Elastic infrastrukturu), 9 (monitorinq) | Sabit və yorucu olmayan əməliyyat |
| **P3:** davamlı | 7 (əhatənin genişləndirilməsi), 10 (proses və sənədlər) | Dəyər artımı |

## Layihənin nəyi dəyişmədən saxlanmalıdır

Aşağıdakılar real mühitdə də düzgündür və yenidən yazılmamalıdır: hər dəyişikliyin PR ilə getməsi, quality gate, code owner təsdiqi, `id`-nin sabit qalması (Kibana eyni `id` ilə yeniləyir), idempotent deploy, `git revert` ilə geri qaytarma (force push yoxdur), `pr-check.yml`-in GitHub-un öz maşınında, `deploy.yml`-in isə runner-də işləməsi.

---

## 1. Hazırlıq: təhvil

- **Sahiblik və lisenziya.** Layihəni 4 nəfər yazıb, `LICENSE` MIT-dir. Real istifadədən əvvəl müəlliflərin razılığı və təlim təşkilatının layihələr barədə qaydası yoxlanmalıdır.
- **Təmiz başlanğıc.** Öz təşkilatınızın **private** repo-sunda təmiz ilk commit ilə başlayın. Köhnə commit tarixçəsində şəxsi e-poçtlar var.
- **Laboratoriya izlərini silin:** VirtualBox təlimatı, simulyasiya hesabatları, demo sənədləri, `sensor-health.md`-dəki lab host adları, test loglarındakı lab host və istifadəçi adları, README-dəki komanda cədvəli və demo rəqəmləri. Demo sənədləri sübut kimi `examples/` qovluğunda qala bilər.
- **Sirlər köçürülmür.** `.env`, parollar, API açarları, runner tokeni yeni mühitdə yenidən yaradılır.

---

## 2. Təhlükəsizlik sərtləşdirməsi

### 2.1 TLS (şifrələnmiş əlaqə)

- **Niyə:** `siem/docker-compose.yml`-də `xpack.security.http.ssl.enabled=false`. Parollar, loglar və API çağırışları şəbəkədə açıq mətnlə gedir. Laboratoriyanın qapalı şəbəkəsində bu məqbuldur, real şəbəkədə yox.
- **Necə:** Elasticsearch HTTP və Kibana üçün TLS aktiv edin, sertifikatı təşkilatın CA-sından alın. Kibana → Elasticsearch əlaqəsi `https` və CA ilə olsun. Winlogbeat-də `ssl.certificate_authorities` əlavə edin. `KIBANA_URL` secret-i `https://...` olsun; daxili CA üçün runner-də `REQUESTS_CA_BUNDLE` təyin edin ki, `requests` sertifikatı yoxlaya bilsin. Elastic sənədində "Set up minimal/basic security plus HTTPS" bölməsinə baxın.
- **Yoxlama:** `curl http://<host>:9200` rədd edilir; Deploy yaşıl bitir; Winlogbeat hadisələri göndərir.

### 2.2 Ən az icazə prinsipi (superuser əvəzinə məhdud açar)

- **Niyə:** `deploy.py` `KIBANA_USER`/`KIBANA_PASS` ilə, laboratoriyada `elastic` superuser hesabı ilə girir. Runner və ya secret ələ keçərsə, bütün SIEM ələ keçir. Ən az icazə (least privilege) prinsipi: hər komponent yalnız işi üçün lazım olanı edə bilməlidir.
- **Necə:** Kibana-da yalnız detection qaydalarını idarə edən rol yaradın (Elastic sənədində "Detections requirements" bölməsi lazımi Kibana və indeks icazələrini sadalayır). Həmin rola API açarı verin. `deploy.py`-də `auth=AUTH` əvəzinə `Authorization: ApiKey <açar>` başlığı istifadə edin, secret-i `KIBANA_API_KEY` adlandırın. Winlogbeat üçün **ayrıca**, yalnız yazma icazəli açar yaradın.
- **Yoxlama:** deploy açarı ilə qayda yaratmaq işləyir, başqa əməliyyatlar (klaster ayarı, istifadəçi yaratmaq) `403` qaytarır.

### 2.3 Sirlərin idarəsi

- **Niyə:** GitHub Secrets repo adminlərinin əlçatanlığındadır, rotasiya yoxdur, sızma halında prosedur yoxdur.
- **Necə:** Açarları təşkilatın secret manager-ində saxlayın (məsələn Vault, bulud provayderinin secret xidməti). Qısa ömürlü açarlar istifadə edin və rotasiya tezliyi təyin edin (məsələn 90 gün). Sızma halı üçün yazılı prosedur: açarı ləğv et, yenisini yarat, Actions jurnallarına bax.
- **Yoxlama:** rotasiyadan sonra Deploy yaşıldır; köhnə açar `401` qaytarır.

### 2.4 Runner izolyasiyası

- **Niyə:** runner SIEM şəbəkəsində işləyir və secrets-ə çatır. Orada icra olunan kod SIEM-ə girişdir.
- **Necə:** (a) runner-i ayrıca host və ya konteynerdə saxlayın; (b) `./config.sh --ephemeral` ilə hər iş üçün təzə runner (iş bitəndə silinir); (c) workflow-da `permissions:` bloku ilə `GITHUB_TOKEN` icazələrini minimuma endirin; (d) üçüncü tərəf action-ları (`actions/checkout@v4` kimi) tag əvəzinə commit SHA ilə sabitləyin; (e) runner yalnız `deploy.yml` üçündür, `pr-check.yml` GitHub-un maşınında qalır; (f) fork-lardan gələn PR-lar runner-ə heç vaxt çatmamalıdır.
- **Yoxlama:** runner-də qalıq fayl yoxdur; PR-dan deploy işə düşmür.

### 2.5 Repo və hüquqlar

- **Niyə:** public repo və şəxsi hesablar real mühit üçün uyğun deyil.
- **Necə:** repo **private** olsun. Branch protection və ruleset imkanları private repoda GitHub planından asılıdır, quraşdırmadan əvvəl planı yoxlayın. `CODEOWNERS`-da şəxs hesabları əvəzinə komandalar yazın (`@təşkilat/detection-reviewers`), hər komandada ən azı 2–3 nəfər olsun. Ruleset-in bypass siyahısı boş qalsın.
- **Yoxlama:** komandaya yeni üzv əlavə etmək CODEOWNERS-i dəyişdirmədən review hüququ verir.

---

## 3. Təcili yol və gecə əhatəsi

**Problem.** Kiçik komandada gecə review verəcək kimsə olmur, amma təcili qayda lazım ola bilər. Laboratoriyada bunun üçün sənədləşdirilmiş yol var ([emergency-deploy.md](emergency-deploy.md)): `Deploy` workflow-nun əl ilə işə salınması və `ref`. O, prosesə və etibara əsaslanır. Real mühitdə həll üç qatdan ibarətdir.

### 3.1 İnsan qatı: gecə əhatəsi (əsas həll)

- **Niyə:** "dörd göz prinsipi" (four-eyes): kritik dəyişikliyi ikinci şəxs görməlidir. Bunu texniki bypass əvəz etmir. Real SOC-lar bunu növbə ilə həll edir.
- **Necə:** on-call cədvəli qurun: hər an əlçatan ən azı 2 reviewer (fərqli vaxt zonaları və ya növbələr). Çağırış kanalı: telefon, SMS və ya paging xidməti. Cavab müddəti razılaşdırın (məsələn 15–30 dəqiqə). Bu, adətən texniki deyil, təşkilati qərardır.
- **Yoxlama:** hər ay bir "sınaq çağırışı": reviewer əlçatandırmı, nə qədər tez cavab verir.

### 3.2 Texniki qat: qapının sərtləşdirilməsi (break-glass)

On-call da cavab vermirsə, təcili yol qalmalıdır, amma nəzarətli. Laboratoriyadakı qapının boşluqlarını bağlayan əlavələr:

| Boşluq | Əlavə | Necə |
|---|---|---|
| İstənilən yazma hüququ olan işə sala bilir | Yalnız on-call komandası | Ayrıca `emergency-deploy.yml` və GitHub **Environment** (`emergency`), icazə yalnız həmin komandaya |
| Səbəb məcburi deyil | Məcburi `reason` və `pr` sahələri | `workflow_dispatch.inputs` ilə, boşdursa iş dayansın |
| Gate deploy-da təkrar işləmir | Deploy-dan əvvəl `validate`, `convert`, `run_tests` | Eyni workflow-da ayrıca job, deploy `needs:` ilə ona bağlansın |
| Heç kim xəbər tutmur | Dərhal bildiriş | Workflow-un əvvəlində Slack/Teams/e-poçt addımı |
| Səhər yoxlaması unudula bilər | Avtomatik issue və SLA | İş başlayanda "təcili review tələb olunur" issue-su açılsın, müddət (məsələn 24 saat) yazılsın |
| Yoxlanmamış qayda qala bilər | Teq ilə işarələmə və təmizlik | Təcili qaydalara `emergency-unreviewed` teqi verin (SOC görsün). SLA keçəndə nəzarət işi onları söndürsün və xəbər versin |

Qeyd: `deploy.py`-nin sonuncu addımı repo-da olmayan `detection-as-code` teqli qaydaları silir. Təcili qayda merge olunmasa, növbəti normal deploy onu zatən silir. Bu davranışı saxlayın.

- **Niyə post-hoc review:** təcili hallarda təsdiq əvvəl yox, **sonra** verilir (break-glass giriş modeli): sürət üçün yoxlama gecikdirilir, amma hər istifadə qeydə alınır və mütləq nəzərdən keçirilir.
- **Yoxlama:** sınaq təcili deploy zamanı: bildiriş gəlir, issue açılır, teq görünür, SLA keçəndə qayda söndürülür.

### 3.3 Təcili ehtiyacın özünü azaltmaq

Gecə təcili ehtiyacın çoxu yeni məntiq yox, **yeni göstəricidir** (zərərli hash, IP, domen). Bunları qaydanın içinə yazmaq əvəzinə ayrıca data faylında (məsələn `iocs/*.yml`) saxlayın, qayda həmin siyahıya baxsın. Beləcə təcili dəyişiklik kiçik, yoxlanması asan data dəyişikliyinə çevrilir və daha aşağı risklə sürətli yola salına bilər.

---

## 4. Mühitlər və təhlükəsiz deploy

### 4.1 Staging və production

- **Niyə:** laboratoriyada tək mühit var: merge edilən qayda birbaşa canlıya çatır. Real mühitdə səhv qayda minlərlə yalançı alert yarada bilər.
- **Necə:** iki mühit qurun: `staging` və `production` (iki ayrı Kibana və ya bir Kibana-da iki **space**; space üçün API yolu `/s/<space>/api/...`). Axın: `main`-ə merge → avtomatik staging-ə deploy → yoxlama → production-a deploy. Production üçün GitHub **Environment** (`production`) yaradın, **required reviewers** və yalnız `main` branch-ından deploy qaydası təyin edin. KIBANA secret-lərini mühit səviyyəsində saxlayın. (Private repoda Environments-in imkanları plandan asılı ola bilər, yoxlayın.)
- **Yoxlama:** staging-də qayda işləmədən production-a getmir; production deploy təsdiq istəyir.

### 4.2 "Nə dəyişəcək" önizləməsi (dry-run)

- **Niyə:** deploy-dan əvvəl nələrin yaradılacağını, yenilənəcəyini və silinəcəyini görmək səhvi yüklənməzdən qabaq tutur.
- **Necə:** `deploy.py`-yə `--plan` rejimi əlavə edin: heç nə dəyişmədən Kibana-dakı vəziyyəti `build/rules.ndjson` ilə müqayisə edib siyahı çıxarsın. PR-da şərh kimi göstərilsin.
- **Yoxlama:** PR-da "3 yeni, 1 yenilənən, 0 silinən" görünür və real deploy ilə üst-üstə düşür.

### 4.3 Kütləvi silmədən qorunma

- **Niyə:** deploy-un 4-cü addımı repo-da olmayan qaydaları silir. Repo səhvən boşalarsa (məsələn səhv branch), bütün qaydalar silinə bilər.
- **Necə:** silinmə `detection-as-code` teqi ilə məhdudlaşır (bu, doğrudur, saxlayın). Üstəlik bir deploy-da müəyyən saydan çox qayda silinəcəksə (məsələn 5-dən çox) iş dayansın və əl ilə təsdiq tələb etsin. Şirkət analitiklərinin əl ilə yaratdığı qaydalara bu teqi verməyin.
- **Yoxlama:** repo-dan 6 qayda silən sınaq PR-ı deploy-da dayanır.

---

## 5. Alert marşrutu

- **Niyə:** laboratoriyada alert yalnız Kibana-da görünür. Real mühitdə kimsə Kibana-ya baxmasa, hadisə görünməz qalır.
- **Necə:** Kibana-nın qayda **action/connector**-larından istifadə edin (e-poçt, Slack, Teams, Jira və ya webhook; bəzi konnektor növləri lisenziya səviyyəsindən asılıdır). `convert.py`-da qaydanın `actions` sahəsini severity-yə görə əlavə edin ki, marşrut da kod kimi idarə olunsun. Nümunə bölgü (şirkət öz SLA-sına görə dəyişdirir): `high` dərhal bildiriş və növbətçiyə çağırış; `medium` ticket; `low` yalnız toplanır, digər siqnallarla birlikdə baxılır. İzləmə üçün Kibana **Cases** və ya ayrıca hadisə idarəetmə sistemi.
- **Yoxlama:** sınaq alertləri hər severity üçün düzgün kanala çatır.

---

## 6. Tuning və istisnalar

- **Niyə:** hər mühitdə "normal" fərqlidir. İlk həftələrdə yalançı alertlər qaçılmazdır; tuning edilməsə analitik alertlərə etibarı itirir (alert yorğunluğu).
- **Necə:**
  1. **Audit dövrü (2–4 həftə):** yeni qaydalar yalnız toplayır (bildirişsiz və ya aşağı severity), yalançı müsbət dərəcəsi ölçülür.
  2. **İstisnalar kod kimi:** Elastic-in qayda istisna (exception) mexanizmindən istifadə edin. İstisnaları qaydanı dəyişdirmədən repo-da saxlayın (məsələn `exceptions/<qayda-id>.yml`) və `deploy.py` onları API ilə yükləsin. Hər istisnada səbəb, sahib və bitmə tarixi olsun.
  3. **Ölçmə:** hər qayda üçün alert sayı və həqiqi/yalançı nisbəti; aylıq baxış.
- **Yoxlama:** tuning-dən sonra eyni qayda eyni hadisəyə baxmayaraq səs-küy yaratmır, `positive.json` testi isə hələ də keçir.

---

## 7. Log mənbələri və əhatə

### 7.1 Mənbə uyğunluğu

- **Niyə:** qaydalar Windows Sysmon hadisələrinə (proses yaratma, registry) əsaslanır. Şirkətdə Linux, firewall, Active Directory, bulud logları da olur.
- **Necə:** hər yeni mənbə üçün: (a) loglar necə gəlir (Beats və ya Elastic Agent); (b) sahə xəritəsi sənədi ([field-mapping.md](field-mapping.md) kimi); (c) `rules/` altında ayrıca qovluq; (d) həmin mənbənin sağlamlıq qaydası (9-cu bölmə).
- **Sysmon konfiqurasiyası:** qaydalar Sysmon-un konfiqurasiyasından asılıdır. Konfiq bir hadisə növünü filtr edirsə, ona əsaslanan qayda **səssiz qalır**. Şirkətin Sysmon konfiqini repo-da versiyalayın (məsələn `sysmon/`) və qaydaların asılı olduğu event ID-ləri sənədləşdirin.
- **Winlogbeat → Elastic Agent keçidi:** `convert.py`-dakı `WINLOGBEAT_FIX` `.caseless` sahəsini çıxarır, çünki Winlogbeat-də bu alt sahə yoxdur. Elastic Agent istifadə olunacaqsa, həmin düzəlişin lazımlığı yenidən yoxlanmalı və bütün testlər təkrar işlədilməlidir.

### 7.2 Əhatənin genişləndirilməsi

- **Niyə:** 20 qayda kiçik əhatədir.
- **Necə:** `scripts/report.py`-nin ATT&CK əhatə hesabatından boşluqları görün. Prioritet: təşkilatın real təhdid modelinə uyğun texnikalar. Yeni qaydaları Atomic Red Team ilə **yalnız izolə edilmiş test mühitində və snapshot-dan sonra** sınayın, nəticələri `simulation-results.md` kimi saxlayın.
- **Yoxlama:** əhatə hesabatında hədəf texnikalar yaşıl olur.

---

## 8. Elastic infrastrukturu

- **Niyə:** laboratoriyada tək node və məhdud yaddaş (`mem_limit`) var; node itərsə log və qaydalar itər.
- **Necə:** (a) ölçü: gündəlik log həcminə görə node sayı və disk (Elastic sənədində sizing bələdçisi); production üçün çox node (məsələn 3) və replika; (b) saxlama müddəti: indeks həyat dövrü siyasəti (ILM), nə qədər müddət saxlanacağı hüquqi və biznes tələbinə görə; (c) ehtiyat nüsxə: snapshot repository və cədvəl, bərpa sınağı; (d) lisenziya: istifadə olunacaq funksiyaların (konnektor növləri, maşın öyrənməsi) lisenziyanızda açıq olub-olmadığını yoxlayın.
- **Pəncərə və gecikmə:** qaydalar hər 5 dəqiqədən bir işləyir və son 6 dəqiqəyə baxır (`convert.py`: `interval`, `from`). Loglar bundan çox gecikərsə (şəbəkə, növbə), hadisə qaçırılır. Real gecikməni ölçün və `from`-u buna uyğun artırın.
- **Yoxlama:** bir node söndürülür, SIEM işləməyə davam edir; snapshot-dan bərpa sınağı uğurlu keçir.

---

## 9. Sensor sağlamlığı və əməliyyat monitorinqi

- **Niyə:** laboratoriyadakı tamper qaydası və heartbeat ([sensor-health.md](sensor-health.md)) bir host üçündür. Sensor susarsa SIEM kor qalır, bunu görməyin yolu "heç nə gəlmir" siqnalıdır.
- **Necə:**
  1. **Hər host/qrup üçün heartbeat:** Kibana-nın Elasticsearch query qaydasını (şərt: sənədlər sayı müəyyən pəncərədə 1-dən az) hostlar üzrə qruplaşdırma ilə qurun ki, hər sensor ayrıca izlənsin.
  2. **Deploy uğursuzluğu bildirişi:** Actions-da uğursuz Deploy kimə və hansı kanala xəbər verir, yazılı olsun.
  3. **Runner nəzarəti:** runner offline olarsa xəbərdarlıq (laboratoriyada bu "Queued" qalma kimi görünür).
  4. **Sapma (drift) yoxlaması:** gecə işi Kibana-dakı qaydaları repo ilə müqayisə edib fərq tapsa bildirsin (kimsə Kibana-da əl ilə dəyişibsə).
- **Yoxlama:** test sensoru söndürülür və xəbərdarlıq gəlir; runner söndürülür və xəbərdarlıq gəlir.

---

## 10. Proses və sənədlər

- **Niyə:** alert gələndə analitikin nə edəcəyi aydın deyilsə, texniki sistem tək başına kifayət etmir.
- **Necə:**
  - Hər qayda üçün qısa **runbook**: alert nə deməkdir, hara baxmalı, yalançı müsbəti necə ayırmalı, nə vaxt eskalasiya. Metadata standartına `references` və ya runbook linki sahəsi əlavə etmək olar ([metadata-standard.md](metadata-standard.md)).
  - **Sahiblik cədvəli:** kim qaydaları yazır, kim yoxlayır, kim SIEM-i işlədir, kim runner və Elastic-ə baxır, kontaktlar.
  - **Dəyişiklik və buraxılış:** əhəmiyyətli dəyişikliklərdə release teqi (məsələn `v1.4`) yaradın, geri qaytarmaq üçün hədəf `ref` asan tapılsın.
  - **Onboarding:** yeni üzv üçün [user-guide.md](user-guide.md) və bir test PR-ı.
- **Yoxlama:** yeni üzv bir test qaydasını təlimata baxaraq, kömək almadan PR-dan canlıya çatdıra bilir.

---

## Qısa yoxlama siyahısı (istehsala çıxmazdan əvvəl)

- [ ] Repo private, bypass siyahısı boş, CODEOWNERS komandalara bağlı
- [ ] TLS aktiv, parollar secret manager-dədir
- [ ] Deploy məhdud API açarı ilə işləyir (superuser yox)
- [ ] Runner izolə olunub (ephemeral və ya ayrıca host), action-lar SHA ilə sabitlənib
- [ ] Staging və production ayrıdır, production deploy təsdiq istəyir
- [ ] Gecə əhatəsi (on-call) və təcili yol qaydası yazılıb və sınaqdan keçib
- [ ] Alertlər kanallara çatır (severity üzrə)
- [ ] Audit dövrü və istisna mexanizmi planlaşdırılıb
- [ ] Hər sensor üçün heartbeat, deploy və runner üçün xəbərdarlıq var
- [ ] Elastic: replika, ILM və snapshot, bərpa sınağı
- [ ] Runbook-lar və sahiblik cədvəli hazırdır
- [ ] Laboratoriya izləri təmizlənib, sirlər yenidən yaradılıb
