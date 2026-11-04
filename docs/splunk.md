# Splunk-a çevirmə (bonus, addım 33)

Sigma qaydaları SIEM-dən asılı deyil. Eyni qayda Elastic-dən başqa Splunk-a da çevrilə bilir.

## Quraşdırma və çevirmə
    sigma plugin install splunk
    sigma convert -t splunk -p splunk_windows rules/ -o build/splunk-queries.txt

`-p splunk_windows` Sigma sahə adlarını (Image, CommandLine) Splunk-un Windows sahələrinə uyğunlaşdırır.

## Nümunə: eyni qayda, iki SIEM
Qayda: `rules/discovery/whoami_execution.yml`

| SIEM | Sorğu |
|---|---|
| Elastic (convert.py) | `process.executable:*\\whoami.exe` |
| Splunk | `Image IN ("*\\whoami.exe", "*\\WHOAMI.EXE")` |

## Nəticə
- 20 qaydanın 18-i Splunk SPL-ə çevrildi.
- Sadə qaydalar (`endswith`, `contains`) birbaşa `Image IN (...)` sorğusuna çevrilir.
- `|re` (regex) istifadə edən qaydalar `| regex` / `| rex` əmrlərinə çevrilir. Real Splunk-da onlar `index=<windows-indeksi>` ilə başlamalıdır.

## Məhdudiyyətlər
- `net_group_domain_admins` və `vssadmin_delete_shadows` qaydaları boş çevrilir: bütün şərtləri `|re` ilə yazılıb və pySigma 1.x ilə uyğun Splunk backend belə qaydalarda sorğu yaratmır. pySigma 2.x-də hər ikisi çevrilir, amma o versiya Elastic backend-imizlə uyğun deyil. Həll: bu qaydaları `|re` əvəzinə `|contains` ilə yenidən yazmaq.
- Splunk-da real test edilməyib (komandada Splunk serveri yoxdur), yalnız çevrilmə yoxlanılıb.
- Bu çevirmə CI-a qoşulmayıb. Əsas SIEM Elastic-dir.