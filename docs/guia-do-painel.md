# Guia do painel

Como usar o painel e interpretar o que ele mostra. Não é preciso saber programar. Com o ambiente
local no ar ([como subir](../README.md#comece-em-cinco-minutos)), o painel fica em
<http://localhost:5173>.

## Em três passos

1. Escolha o **indicador**, como Mortes Violentas Intencionais ou Feminicídio.
2. Escolha a **unidade da federação (UF)** em foco. Os cartões e o gráfico de evolução mudam para ela.
3. Escolha o **ano do ranking** e o critério em **Classificar por**. O ranking, o mapa e os cartões
   mudam para esse ano.

Tudo é atualizado sem recarregar a página.

## Filtros

| Filtro | O que faz | Quando aparece |
| --- | --- | --- |
| Indicador | Define o crime analisado. Os subtipos ficam recuados sob o indicador principal. | Sempre. "Furto" fica desativado, porque não há total de furtos: escolha veículo ou celular. |
| Região | Limita a lista de UFs e o ranking à região e esmaece as demais no mapa. A posição continua sendo entre as 27 UFs. | Sempre |
| Unidade da federação | Escolhe a UF dos cartões e do gráfico de evolução. | Sempre |
| Ano do ranking | Escolhe o ano do ranking, do mapa e dos cartões. O gráfico de evolução sempre mostra todos os anos. | Sempre |
| Classificar por | Taxa, número absoluto ou participação. | Sempre; a participação só aparece quando o indicador tem uma referência. |
| Unidade | Vítimas ou ocorrências. | Só em homicídio doloso, latrocínio e lesão corporal seguida de morte. |
| Corporação e situação | Polícia Civil ou Militar, em serviço ou fora de serviço. | Só em morte decorrente de intervenção policial. |

Você também pode selecionar uma UF clicando na barra dela ou no estado no mapa.

## Blocos da página

- **Cartões:** taxa, variação da taxa em relação ao ano anterior, posição entre as UFs e número
  absoluto da UF no ano escolhido, com a situação do dado e as notas do FBSP.
- **Evolução ao longo dos anos:** linhas da UF, da sua região e do Brasil. Os anos revisados pelo
  FBSP ficam marcados. Com um recorte de corporação, só a UF aparece, porque nem todas as UFs informam
  esses dados e os totais não seriam comparáveis.
- **Comparação entre estados:** barras ordenadas pelo critério escolhido, com a UF selecionada em
  destaque.
- **Mapa:** UFs coloridas em cinco faixas, cada uma com cerca de um quinto das UFs. A UF selecionada
  tem borda laranja.

## Como ler os números

| Termo | Significado |
| --- | --- |
| Taxa | Número de casos em relação à base indicada no título do gráfico, em geral 100 mil habitantes. Permite comparar UFs de tamanhos diferentes. |
| Base da taxa | 100 mil habitantes na maioria; 100 mil mulheres em feminicídio e homicídio de mulheres; 100 mil veículos em roubo e furto de veículos; 100 instituições em roubo a instituição financeira. |
| Variação | Mudança percentual da taxa em relação ao ano anterior. |
| Posição | Lugar entre as 27 UFs, da maior para a menor. Empates dividem a posição (1, 2, 2, 4). |
| Participação | Parte do indicador no indicador acima dele (mortes por intervenção policial dentro das MVI, por exemplo) ou, em um recorte, no total do indicador. |
| Vítimas e ocorrências | Um mesmo fato pode ter mais de uma vítima, então os dois números são diferentes. |
| Fenômeno inexistente | O FBSP marcou "-": o valor é zero. |
| Informação não disponível | O FBSP marcou "...": a UF não informou. Isso não significa zero. A UF fica sem posição, no fim do ranking. |

Cuidados ao tirar conclusões:

- **Subtipos não somam o total.** Uma ocorrência pode entrar em mais de um subtipo de roubo.
- **Taxas com bases diferentes não se comparam.** Não compare uma taxa por 100 mil veículos com outra
  por 100 mil habitantes.
- **Números podem ser revisados.** Se o FBSP mudou um número entre edições, o valor anterior aparece na
  nota, e uma revisão grande pode afetar a variação daquele ano.
- **Variação em branco é intencional.** A taxa por 100 mil mulheres de 2023 não tem variação porque o
  denominador mudou entre 2022 e 2023.

## Exportar e compartilhar

- **CSV:** em cada gráfico, use **Baixar estes dados (CSV)**. O arquivo usa vírgula como separador e
  ponto como decimal. No Excel em português, importe por **Dados > De Texto/CSV**, em vez de abrir com
  dois cliques, e escolha a vírgula como delimitador e o ponto como separador decimal.
- **Tabela:** **Ver os dados em tabela** mostra os números de cada gráfico.
- **Link:** a seleção fica no endereço da página. Copie-o para compartilhar exatamente a mesma visão,
  por exemplo `/?indicador=feminicidio&uf=BA`.

## Acessibilidade

- **Teclado:** todos os controles funcionam com Tab. No mapa, entre com Tab, navegue pelas UFs com as
  setas e selecione com Enter. **Pular para o conteúdo** é a primeira parada.
- **Leitores de tela:** cada gráfico tem título, descrição e uma tabela equivalente.
- **Cores:** a paleta foi escolhida para distinguir as séries nos tipos comuns de daltonismo, e as
  linhas também diferem pelo traço e pelo marcador.
- **Tema:** o painel segue o tema do sistema até você usar o botão no topo; a escolha fica salva no
  navegador.
- **Celular:** em telas estreitas, os blocos ficam em uma coluna.

## Se algo não aparecer

| Sintoma | O que fazer |
| --- | --- |
| "Não foi possível carregar os dados" | A API está fora do ar ou os dados não foram importados. Veja a [solução de problemas](guia-de-operacao.md#solução-de-problemas). |
| O mapa mostra um aviso | O arquivo da malha das UFs não foi encontrado; o restante do painel funciona. Veja [`frontend/public/README.md`](../frontend/public/README.md). |
| Um filtro voltou sozinho ao padrão | O link trazia um valor que não existe, como uma UF inválida, e o painel o corrigiu. |
