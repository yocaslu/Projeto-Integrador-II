// Tabela com os mesmos números do gráfico, recolhida por padrão. Leitores de tela e quem
// prefere ler os valores exatos não dependem do SVG (RNF01).
export default function TabelaDados({ legenda, colunas, linhas }) {
  return (
    <details className="tabela-dados">
      <summary>Ver os dados em tabela</summary>
      <div className="tabela-dados__rolagem">
        <table>
          <caption>{legenda}</caption>
          <thead>
            <tr>
              {colunas.map((coluna) => (
                <th key={coluna.chave} scope="col">
                  {coluna.titulo}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {linhas.map((linha) => (
              <tr key={linha.chave}>
                {colunas.map((coluna, indice) =>
                  indice === 0 ? (
                    <th key={coluna.chave} scope="row">
                      {linha[coluna.chave]}
                    </th>
                  ) : (
                    <td key={coluna.chave}>{linha[coluna.chave]}</td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
