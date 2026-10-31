// Cálculos do mapa coroplético (RF06), separados do Leaflet para serem testados sem DOM.

// Escala sequencial de um só matiz (azuis), legível em qualquer tipo de daltonismo (RNF01). Cinco
// classes bastam para 27 UFs. Os valores ficam em global.css: no tema claro, quanto mais alto o
// valor, mais escura a cor; no escuro, mais clara, para se destacar do fundo.
export const ESCALA = [1, 2, 3, 4, 5].map((classe) => `var(--mapa-classe-${classe})`);
export const COR_SEM_DADO = "var(--mapa-sem-dado)";

// Classes por quantis: cada cor reúne um número parecido de UFs, o que evita um mapa quase
// todo de uma cor quando uma ou duas UFs têm taxa muito alta.
export function classificar(valores, classes = ESCALA.length) {
  const ordenados = valores.filter((valor) => valor !== null && valor !== undefined).sort((a, b) => a - b);
  if (ordenados.length === 0) return [];
  const limites = [];
  for (let indice = 0; indice < classes; indice += 1) {
    const inicio = ordenados[Math.floor((indice * ordenados.length) / classes)];
    const fimIndice = Math.floor(((indice + 1) * ordenados.length) / classes) - 1;
    const fim = ordenados[Math.max(fimIndice, 0)];
    // Com poucas UFs, duas classes podem coincidir; elas são unidas.
    const anterior = limites.at(-1);
    if (anterior && inicio <= anterior.fim) {
      anterior.fim = Math.max(anterior.fim, fim);
    } else {
      limites.push({ inicio, fim });
    }
  }
  return limites.map((limite, indice) => ({
    ...limite,
    cor: ESCALA[Math.round((indice * (ESCALA.length - 1)) / Math.max(limites.length - 1, 1))],
  }));
}

export function corDoValor(valor, classes) {
  if (valor === null || valor === undefined) return COR_SEM_DADO;
  const classe = classes.find((item) => valor <= item.fim) ?? classes.at(-1);
  return classe?.cor ?? COR_SEM_DADO;
}

// Retângulo que envolve a malha, no formato do Leaflet: [[lat mín., lng mín.], [lat máx., lng máx.]].
export function limitesDaMalha(geojson) {
  let latMin = Infinity;
  let latMax = -Infinity;
  let lngMin = Infinity;
  let lngMax = -Infinity;
  const percorrer = (coordenadas) => {
    if (typeof coordenadas[0] === "number") {
      const [lng, lat] = coordenadas;
      latMin = Math.min(latMin, lat);
      latMax = Math.max(latMax, lat);
      lngMin = Math.min(lngMin, lng);
      lngMax = Math.max(lngMax, lng);
      return;
    }
    coordenadas.forEach(percorrer);
  };
  geojson.features.forEach((feicao) => percorrer(feicao.geometry.coordinates));
  return [
    [latMin, lngMin],
    [latMax, lngMax],
  ];
}
