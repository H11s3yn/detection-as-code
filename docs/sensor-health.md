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

Bu, Sigma/EQL qaydası deyil, Kibana tərəfində qurulan ayrı bir qayda tipidir. Addımlar:

1. Kibana → Security → Rules → **Create new rule** → **Threshold**.
2. Index: `winlogbeat-*`. Query: `host.name : "VM2"` (və ya `agent.name`).
3. Threshold: `host.name`, **count < 1** (son 15 dəqiqədə).
4. Interval: 5m, from `now-15m`. Severity: high.
5. Ad: "VM2 loq axını dayandı (sensor sağlamlığı)".

> Qeyd: bəzi Kibana versiyalarında "count < 1" əvəzinə bir indicator-absence / EQL `sequence ... with maxspan` üsulu da işlədilə bilər. Əsas fikir: müəyyən pəncərədə host-dan hadisə **gəlmirsə**, alert.

## Dəstəkləyən telemetriya (istəyə bağlı)

Daha dəqiq olmaq üçün Winlogbeat-ə bu jurnalları da əlavə etmək olar:

- **Windows System jurnalı** — Service Control Manager hadisələri: 7036 (xidmət dayandı), 7045 (yeni xidmət quraşdırıldı).
- **Sysmon-un öz hadisəsi** — Event 4: Sysmon xidmətinin vəziyyəti dəyişdi (başladı/dayandı).

Bu jurnallar endpoint konfiqində (Winlogbeat `winlogbeat.yml`) açılır və Kibana-da yoxlanır; Sigma pipeline-dan keçmir.
