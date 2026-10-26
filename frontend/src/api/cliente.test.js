import { converterRegistro, paraNumero } from "./cliente.js";

test("converte texto decimal em número", () => {
  expect(paraNumero("41.2")).toBe(41.2);
  expect(paraNumero(null)).toBeNull();
  expect(paraNumero("abc")).toBeNull();
});

test("converte os campos numéricos de um registro", () => {
  const registro = converterRegistro({
    valor: "5800",
    taxa: { valor: "40.9", base: "100 mil habitantes", origem: "calculada" },
    taxa_publicada: "40.9",
    variacao: { ano_referencia: 2024, valor_pct: "-3.1", taxa_pct: "-3.6" },
  });

  expect(registro.valor).toBe(5800);
  expect(registro.taxa.valor).toBe(40.9);
  expect(registro.variacao.valor_pct).toBe(-3.1);
});

test("mantém nulos quando o dado não está disponível", () => {
  const registro = converterRegistro({ valor: null, taxa: null, taxa_publicada: null, variacao: null });
  expect(registro.valor).toBeNull();
  expect(registro.taxa).toBeNull();
  expect(registro.variacao).toBeNull();
});
