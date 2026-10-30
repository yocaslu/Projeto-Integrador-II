// Substituto do react-leaflet nos testes do Jest (package.json, moduleNameMapper): o pacote
// é só ESM e o Leaflet precisa de medidas de layout que o jsdom não tem. Cada UF vira um
// item com a cor e a borda calculadas pelo componente, o texto do tooltip e o clique.

export function MapContainer({ children }) {
  return <div data-testid="mapa">{children}</div>;
}

export function GeoJSON({ data, style, onEachFeature }) {
  return (
    <ul data-testid="malha">
      {data.features.map((feicao) => {
        const eventos = {};
        let tooltip = "";
        onEachFeature?.(feicao, {
          bindTooltip: (texto) => {
            tooltip = texto;
          },
          on: (evento, funcao) => {
            eventos[evento] = funcao;
          },
          bringToFront: () => {},
        });
        const { fillColor, color, weight } = style(feicao);
        return (
          <li
            key={feicao.properties.codarea}
            data-codarea={feicao.properties.codarea}
            data-cor={fillColor}
            data-borda={color}
            data-espessura={weight}
            onClick={() => eventos.click?.()}
          >
            {tooltip}
          </li>
        );
      })}
    </ul>
  );
}
