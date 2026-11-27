# Quraşdırma təlimatı

Bu sənəd sistemin nədən ibarət olduğunu və hansı ardıcıllıqla qurulduğunu izah edir. Hər addımın sonunda necə yoxlanacağı yazılıb. Ekran-ekran təfərrüat (VirtualBox, Ubuntu və Windows quraşdırıcısı, şəbəkə) üçün [setup.md](setup.md)-ə baxın. Real mühit üçün əlavə tələblər [production-guide.md](production-guide.md)-dədir.

## Nə qurulur

| Komponent | Harada | Vəzifəsi |
|---|---|---|
| SIEM: Elasticsearch + Kibana 9.5.5 | VM1, Docker Compose | Logları saxlayır, aşkarlama qaydalarını işlədir, alert yaradır |
| GitHub repo + Actions | GitHub | Qaydaların saxlandığı yer; yoxlama (quality gate) və deploy burada başlayır |
| Self-hosted runner | VM1 | Deploy işini SIEM-in yanında icra edir (Kibana-ya `localhost` ilə çatır) |
| Log mənbəyi: Windows + Sysmon + Winlogbeat | VM2 | Əməliyyat sistemi hadisələrini toplayıb Elasticsearch-ə göndərir |

Qaydanın yolu:

```text
Sigma qaydası (YAML) → Pull Request → quality gate → review → merge
      → convert.py (Sigma → EQL) → deploy.py → Kibana → alert
```

## Tələblər

- **VM1 (Ubuntu Server):** laboratoriyada 6 GB RAM, 4 CPU, 50 GB disk istifadə olunub. Docker, Docker Compose, Python 3 və `python3-venv` lazımdır.
- **VM2 (Windows Server 2022):** laboratoriyada 4 GB RAM.
- **GitHub:** repoya admin icazəsi (ruleset, secrets və runner üçün).
- **Şəbəkə:** VM2 → VM1 port 9200 (Elasticsearch); VM1 → GitHub (runner xaricə çıxır).
- **Elasticsearch üçün:** `vm.max_map_count=262144`.

## Addımlar

### 1. Repo-nu götür

```bash
git clone https://github.com/H11s3yn/detection-as-code.git
```

Öz təşkilatınızda istifadə edirsinizsə, əvvəlcə öz repo-nuza kopyalayın və aşağıdakı bütün GitHub addımlarını həmin repoda edin.

### 2. VM1: SIEM

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee /etc/sysctl.d/99-elastic.conf

mkdir -p ~/siem && cp detection-as-code/siem/docker-compose.yml ~/siem/ && cd ~/siem

cat > .env <<EOF
STACK_VERSION=9.5.5
ELASTIC_PASSWORD=$(openssl rand -hex 12)
KIBANA_PASSWORD=$(openssl rand -hex 12)
ENCRYPTION_KEY=$(openssl rand -hex 32)
EOF
chmod 600 .env

docker compose up -d
docker compose ps -a
```

**Yoxlama:** `elasticsearch` → `Up (healthy)`, `setup` → `Exited (0)`, `kibana` → `Up`. Kibana-nın qalxması 1–2 dəqiqə çəkir. Brauzerdə `http://<VM1>:5601`, istifadəçi `elastic`, parol `.env`-dəki `ELASTIC_PASSWORD`.

`.env` faylı repoya əlavə olunmur, ekran şəklinə və söhbətə düşmür.

### 3. GitHub: qoruma, secrets, runner

**a) Ruleset.** Settings → Rules → Rulesets → New branch ruleset: ad `main-protection`, target `main`, Enforcement **Active**, **Bypass list boş**. İşarələnməli olanlar: Restrict deletions; Require a pull request (1 təsdiq, **Require review from Code Owners**); Require status checks (`quality-gate`, branch up to date); Block force pushes.

**b) Secrets.** Settings → Secrets and variables → Actions:

| Ad | Dəyər |
|---|---|
| `KIBANA_URL` | `http://localhost:5601` (runner VM1-dədir) |
| `KIBANA_USER` | Kibana istifadəçisi |
| `KIBANA_PASS` | həmin istifadəçinin parolu |

**c) Runner.** Settings → Actions → Runners → New self-hosted runner → Linux x64. Səhifədəki əmrləri VM1-də işlədin, sonra xidmət kimi quraşdırın:

```bash
sudo ./svc.sh install
sudo ./svc.sh start
```

Qeydiyyat tokeni yalnız həmin səhifədə görünür və heç yerdə paylaşılmır.

**Yoxlama:** GitHub-da runner **Idle** görünür.

**Vacib:** self-hosted runner yalnız `deploy.yml`-də işləyir (main-ə push və əl ilə işə salma). `pr-check.yml` GitHub-un öz maşınında (`ubuntu-latest`) işləyir, PR-dakı yoxlanmamış kod VM1-də icra olunmur. Public repoda bu qayda pozulmamalıdır.

### 4. İlk deploy

Actions → **Deploy** → Run workflow → `main`.

**Yoxlama:** "Kibana-ya yükləmə" addımında `Kibana hazırdır`, sonra `yükləndi: N qayda`. Kibana → Security → Rules → Detection rules: qaydalar `detection-as-code` teqi ilə görünür. Elastic-in öz hazır qaydaları quraşdırılmır, yalnız repodakılar olur.

### 5. VM2: log mənbəyi

Windows Server-də Sysmon və Winlogbeat qurulur, Winlogbeat hadisələri VM1-in `9200` portuna göndərir. Addım-addım əmrlər: [setup.md, Hissə C](setup.md). Nəticədə Kibana → Discover-də `winlogbeat-*` altında VM2 hadisələri görünməlidir.

### 6. Uçdan-uca yoxlama

1. VM2-də `whoami` icra et.
2. 5–6 dəqiqə gözlə (qaydalar 5 dəqiqədən bir işləyir).
3. Kibana → Security → Alerts: **"whoami əmrinin icrası"** alerti, host VM2-nin adı.

Alert gəlirsə, bütün zəncir işləyir: log mənbəyi → SIEM → deploy olunmuş qayda.

## Quraşdırma bitdi: son siyahı

- [ ] Kibana açılır və `elastic` ilə giriş olur
- [ ] Ruleset `main-protection` aktivdir, bypass siyahısı boşdur
- [ ] 3 secret əlavə olunub
- [ ] Runner **Idle** göstərir
- [ ] İlk Deploy yaşıl bitib, qaydalar Kibana-dadır
- [ ] VM2 hadisələri Discover-də görünür
- [ ] `whoami` alerti gəlib
- [ ] VM1 və VM2-nin saatları düzgündür (aşağıya bax)

## Ən çox rast gəlinən problemlər

| Əlamət | Səbəb | Həll |
|---|---|---|
| Alert gəlmir, "Last run 9 hours ago" | VM1-in saatı geri qalıb | `sudo systemctl restart chrony && sudo chronyc makestep` |
| Deploy saatlarla "Queued" qalır | VM1 sönülüdür və ya runner işləmir | VM1-i açın, `sudo systemctl restart actions.runner.*` |
| Qayda heç vaxt alert vermir, hadisə isə var | `.caseless` sahəsi Winlogbeat-də yoxdur | `convert.py`-dəki `WINLOGBEAT_FIX` (artıq tətbiq olunub, saxlayın) |
| "Kibana server is not ready yet" | Kibana hələ qalxır | 1–2 dəqiqə gözləyin |

Tam siyahı: [setup.md, Problemlər və həlli](setup.md).

## Bu təlimat nəyi əhatə etmir

Burada qurulan sistem **laboratoriya** üçündür: HTTP (TLS yoxdur), `elastic` superuser hesabı, tək node, tək mühit. Real mühitdə nələrin dəyişməli olduğu, niyə və necə: [production-guide.md](production-guide.md).
