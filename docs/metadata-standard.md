# Qayda metadata standartı

Hər Sigma qaydasında bu sahələr məcburidir.

| Sahə | Qayda |
|---|---|
| title | Qısa, aydın ad |
| id | UUID, hər qayda üçün unikal |
| status | experimental / test / stable / deprecated |
| description | Qaydanın nəyi aşkarladığı |
| author | Müəllif |
| date | Dırnaqda yazılır: '2026-10-27' |
| tags | Ən azı 1 attack.<tactic> və 1 attack.tXXXX |
| logsource | category və product |
| falsepositives | Boş olmamalıdır |
| level | informational / low / medium / high / critical |

## Əlavə qaydalar

- Hər qaydanın tests/<id>/positive.json və tests/<id>/negative.json faylı olmalıdır.
- Qayda dəyişəndə id dəyişmir, çünki Kibana-da eyni id ilə yenilənir.
- Qaydalar rules/<tactic>/ qovluğuna qoyulur.