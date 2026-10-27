# Töhfə qaydası

## Branch adları

- rule/<ad>: yeni qayda və ya qayda dəyişikliyi
- chore/<ad>: struktur və konfiqurasiya
- docs/<ad>: sənədlər
- feat/<ad>: skriptlər və avtomatlaşdırma
- fix/<ad>: düzəlişlər

main branch-a birbaşa push olunmur. Yalnız Pull Request ilə, ən azı 1 təsdiqlə.

## Commit formatı

rule: ...
fix: ...
docs: ...
chore: ...
feat: ...

Nümunə: rule: add wmic process call create detection (T1047)

## Hər qayda ayrı PR-da olmalıdır

## Review siyahısı

- [ ] id unikaldır (UUID)
- [ ] Bütün məcburi metadata sahələri var (bax: docs/metadata-standard.md)
- [ ] ATT&CK tactic və technique teqləri düzgündür
- [ ] falsepositives boş deyil
- [ ] tests/<id>/positive.json və negative.json var
- [ ] sigma check rules/ xətasız keçir