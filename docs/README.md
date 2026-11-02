# Documentação

## Para usar

| Arquivo | Conteúdo |
| --- | --- |
| [guia-do-painel.md](guia-do-painel.md) | Como usar o painel: filtros, cartões, gráficos, mapa, CSV, link compartilhável e acessibilidade. |
| [guia-da-api.md](guia-da-api.md) | Receitas de consulta à API, campos de um registro, uso em Python, R e JavaScript, CSV em planilhas, erros e cache. |
| [operacao.md](operacao.md) | Instalação local, importação dos dados, atualização para novas edições, produção, cópia de segurança e problemas comuns. |
| [desenvolvimento.md](desenvolvimento.md) | Testes, integração contínua, como contribuir e como publicar versões. |

## Para entender como foi construído

| Arquivo ou pasta | Conteúdo |
| --- | --- |
| [arquitetura.md](arquitetura.md) | Visão geral da arquitetura do backend, do frontend e da implantação. |
| [contrato-api.md](contrato-api.md) | Contrato completo da API v1 (recursos, parâmetros, formatos, CSV, erros, cache e testes de contrato). Fonte da verdade da API. |
| [importacao.md](importacao.md) | Especificação da importação das planilhas do FBSP e da população do IBGE. |
| [modelagem.md](modelagem.md) | Modelagem de dados: entidades, atributos, restrições e decisões. Fonte da verdade da modelagem. |
| [modelagem/](modelagem/) | Diagrama entidade-relacionamento (fonte `.dot` e imagens). |
| [api/openapi.yaml](api/openapi.yaml) | Esquema OpenAPI 3 gerado pelo drf-spectacular e versionado (o CI confere o diff). |
| [adr/](adr/) | Registros de decisões de arquitetura (0001 a 0012). |
| [design/](design/) | Esboços da interface e registros das etapas de Design Thinking. |
| [imagens/](imagens/) | Capturas da interface usadas nos guias. |

O roteiro do projeto (objetivos, requisitos e fundamentação) é mantido no documento compartilhado do
grupo. Onde ele e os arquivos acima divergirem sobre a API, a importação ou a modelagem, valem os
arquivos acima.
