# Sensorun sağlamlığı: Sysmon söndürülməsini tutmaq

Bütün aşkarlamamız VM2-dəki **Sysmon** loglarına əsaslanır. Hücumçu əvvəlcə Sysmon-u susdursa, sonrakı hərəkətləri görünməz qalır. Bu, sistemimizin əsl kor nöqtəsidir. İki qatla bağlayırıq.

## Qat 1 — əmr sətri ilə dayandırma (bu repoda var)

`rules/defense_evasion/sysmon_tamper.yml` (high) bu əmrləri tutur:

| Üsul | Nümunə |
|---|---|
| Xidməti dayandır | `sc stop Sysmon64`, `net stop Sysmon64` |
| PowerShell | `Stop-Service Sysmon64` |
| Sil | `sc delete Sysmon64` |
| Uninstall | `sysmon64 -u force` |
| Sürücünü boşalt | `fltMC unload SysmonDrv` |
| Prosesi öldür | `taskkill /im Sysmon64.exe /f` |

**Məhdudiyyət:** bu, proses-yaratma qaydasıdır, yəni yalnız **əmr sətri** üsullarını görür. Hücumçu `services.msc` (menyu) ilə və ya birbaşa Windows API ilə xidməti dayandırsa, bu qayda kor qalır. Eyni dərs: əmrə yox, effektə bax.

## Qat 2 — sükutu tutmaq ("dead man's switch")

Ölü sensordan öz ölümünü bildirməsini gözləmək olmaz. Ona görə **loqun kəsilməsinə** baxırıq: VM2 normalda hər bir neçə dəqiqədə müəyyən sayda hadisə göndərir. Əgər bir müddət **0** göndərsə, alert yarat. Bu üsul Sysmon-un hansı yolla (dayandırma, kill, uninstall, menyu, hətta şəbəkəni çəkmək) dayandırıldığından asılı deyil, çünki konkret əmrə yox, **boşluğa** baxır.

Bunu Kibana-nın **Elasticsearch query** qayda tipi ilə qururuq. Diqqət: Security "Threshold" qaydası yalnız "sayı N-dən **çoxdursa**" deyə bilir, "sıfırdırsa" yox. "Elasticsearch query" qaydasında isə "**is below**" şərti var, absence (sükut) üçün lazım olan budur.

1. Kibana → **Stack Management** → Alerts and Insights → **Rules** → **Create rule**.
2. Rule type: **Elasticsearch query**.
3. Index: `winlogbeat-*`, time field: `@timestamp`.
4. Query (KQL): `agent.name : "<VM2-nin host adı>"` (məs. `WIN-IPP7HCDVL8N`; dəqiq adı Discover-də yoxla).
5. Şərt: **WHEN count IS BELOW 1 FOR THE LAST 15 minutes**.
6. Check every: 5 minutes. İstəsən bir action (index / email / Slack connector) əlavə et.
7. Ad: "VM2 loq axını dayandı (sensor sağlamlığı)".

Məntiq: VM2 sağlam ikən hər 15 dəqiqədə ≥1 hadisə gəlir → şərt yalan → alert yoxdur. Sysmon və ya Winlogbeat dayananda say 0 olur → şərt doğru → alert. Dayandırma üsulu (əmr, menyu, API, şəbəkəni çəkmək) fərq etmir, çünki hadisənin **olmamasına** baxırıq.

## Dəstəkləyən telemetriya (istəyə bağlı)

Daha dəqiq olmaq üçün Winlogbeat-ə bu jurnalları da əlavə etmək olar:

- **Windows System jurnalı** — Service Control Manager hadisələri: 7036 (xidmət dayandı), 7045 (yeni xidmət quraşdırıldı).
- **Sysmon-un öz hadisəsi** — Event 4: Sysmon xidmətinin vəziyyəti dəyişdi (başladı/dayandı).

Bu jurnallar endpoint konfiqində (Winlogbeat `winlogbeat.yml`) açılır və Kibana-da yoxlanır; Sigma pipeline-dan keçmir.
