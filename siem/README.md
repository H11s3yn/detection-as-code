# SIEM: Elasticsearch + Kibana (Docker Compose)

VM1-də (Ubuntu) işə salmaq:

```bash
sudo sysctl -w vm.max_map_count=262144
echo 'vm.max_map_count=262144' | sudo tee /etc/sysctl.d/99-elastic.conf

cd siem
cat > .env <<EOF
STACK_VERSION=9.5.5
ELASTIC_PASSWORD=$(openssl rand -hex 12)
KIBANA_PASSWORD=$(openssl rand -hex 12)
ENCRYPTION_KEY=$(openssl rand -hex 32)
EOF

docker compose up -d
docker compose ps -a
```

Kibana: http://localhost:5601 — istifadəçi `elastic`, parol `.env`-dəki `ELASTIC_PASSWORD`.

`.env` faylı repoya **əlavə olunmur**.