# Arquitetura

A aplicação segue o estilo REST (Fielding, 2000): o backend expõe os dados tratados como recursos
de uma API somente leitura, e o frontend os consome para montar o dashboard.

```
Planilhas FBSP e IBGE ──> importar_anuario ──> PostgreSQL 18
                                                   │
                                     Django + DRF (/api/v1/)
                                                   │
                         Traefik ──> React (Recharts, Leaflet)
```

| Camada | Tecnologia |
| --- | --- |
| Banco de dados | PostgreSQL 18 |
| Backend | Python 3.14, Django 6.1, Django REST Framework, django-filter, drf-spectacular |
| Importação | pandas, openpyxl e odfpy |
| Frontend | React, Recharts e Leaflet |
| Testes | pytest, Jest, Playwright e axe-core |
| Infraestrutura | Proxmox VE, Ubuntu Server, Docker, Traefik e Gunicorn |
| Integração contínua | GitHub Actions |
