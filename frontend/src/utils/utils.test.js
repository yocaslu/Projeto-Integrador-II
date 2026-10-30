import { metadados } from "../testes/respostas.js";
import {
  formatarInteiro,
  formatarTaxa,
  formatarVariacao,
  rotuloTaxa,
  SEM_DADO,
} from "./formatacao.js";
import { achatarIndicadores } from "./indicadores.js";

test("formata números no padrão brasileiro", () => {
  expect(formatarInteiro(3615)).toBe("3.615");
  expect(formatarTaxa(7.8)).toBe("7,80");
  expect(formatarVariacao(-3.85)).toBe("−3,85%");
  expect(formatarVariacao(2)).toBe("+2,00%");
  expect(formatarVariacao(0)).toBe("0,00%");
});

test("mostra a ausência de dado em vez de zero", () => {
  expect(formatarInteiro(null)).toBe(SEM_DADO);
  expect(formatarTaxa(undefined)).toBe(SEM_DADO);
  expect(formatarVariacao(null)).toBe(SEM_DADO);
});

test("monta o rótulo da taxa a partir da base", () => {
  expect(rotuloTaxa("100 mil mulheres")).toBe("Taxa por 100 mil mulheres");
  expect(rotuloTaxa(null)).toBe("Taxa");
});

test("achata a árvore de indicadores na ordem da hierarquia, com o nível", () => {
  const lista = achatarIndicadores(metadados.indicadores);
  expect(lista.map((item) => [item.slug, item.nivel])).toEqual([
    ["mvi", 0],
    ["feminicidio", 1],
    ["furto", 0],
  ]);
  expect(lista[2].possui_registros).toBe(false);
});
