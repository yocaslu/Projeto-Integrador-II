# Documentação

## Guias práticos

| Guia | Para quem | Conteúdo |
| --- | --- | --- |
| [guia-do-painel.md](guia-do-painel.md) | Quem consulta os dados | Filtros, leitura dos números, exportação, acessibilidade. |
| [guia-da-api.md](guia-da-api.md) | Quem integra ou analisa | Receitas em `curl` e Python, CSV, erros, paginação e cache. |
| [guia-de-operacao.md](guia-de-operacao.md) | Quem instala ou mantém | Ambiente, importação, testes, produção, backup, versões e solução de problemas. |

## Referência técnica

| Arquivo ou pasta | Conteúdo |
| --- | --- |
| [contrato-api.md](contrato-api.md) | Contrato completo da API v1 (fonte da verdade): recursos, parâmetros, formatos, CSV, erros, cache e testes de contrato. |
| [api/openapi.yaml](api/openapi.yaml) | Esquema OpenAPI 3 gerado pelo drf-spectacular e versionado (o CI confere o diff). |
| [importacao.md](importacao.md) | Especificação da importação das planilhas do FBSP e das bases do IBGE. |
| [modelagem.md](modelagem.md) | Modelagem de dados (fonte da verdade): entidades, atributos, restrições e decisões. |
| [modelagem/](modelagem/) | Diagrama entidade-relacionamento (fonte `.dot` e imagens). |
| [arquitetura.md](arquitetura.md) | Visão geral da arquitetura e das ferramentas. |
| [adr/](adr/) | Registros de decisões de arquitetura. |
| [design/](design/) | Esboços da interface e registros das etapas de Design Thinking. |
| [imagens/](imagens/) | Capturas da interface. |

O roteiro do projeto (objetivos, requisitos e texto do relatório final) é mantido no documento
compartilhado do grupo. Para a API, a importação e a modelagem, valem os arquivos acima.
