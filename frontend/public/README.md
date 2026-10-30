# Arquivos públicos

Arquivos servidos sem processamento pelo Vite.

## Malha das UFs (`malhas/ufs.json`)

O mapa (RF06) lê a malha das 27 UFs de `public/malhas/ufs.json`, baixada **uma vez** da API de
malhas territoriais do IBGE e versionada, para que o mapa não dependa da disponibilidade do IBGE
a cada visita. Para gerar ou atualizar o arquivo, com acesso à internet:

```bash
cd frontend
npm run malha
```

O script (`scripts/baixar-malha.mjs`) consulta
`https://servicodados.ibge.gov.br/api/v3/malhas/paises/BR?formato=application/vnd.geo+json&qualidade=minima&intrarregiao=UF`,
confere que vieram 27 UFs, mantém em cada feição só a propriedade `codarea` (código IBGE da UF,
que liga a malha ao campo `localidade.codigo_ibge` da API) e arredonda as coordenadas a 4 casas.
Depois, faça o commit do arquivo (`chore(dados): adiciona malha das UFs do IBGE`).

Sem o arquivo, o painel continua funcionando e o bloco do mapa mostra um aviso no lugar do mapa.
