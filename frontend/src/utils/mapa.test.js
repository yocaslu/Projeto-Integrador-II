import { malha } from "../testes/respostas.js";
import { classificar, COR_SEM_DADO, corDoValor, ESCALA, limitesDaMalha } from "./mapa.js";

test("divide as taxas em cinco classes por quantis, ignorando nulos", () => {
  const valores = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, null];
  expect(classificar(valores)).toEqual([
    { inicio: 1, fim: 2, cor: ESCALA[0] },
    { inicio: 3, fim: 4, cor: ESCALA[1] },
    { inicio: 5, fim: 6, cor: ESCALA[2] },
    { inicio: 7, fim: 8, cor: ESCALA[3] },
    { inicio: 9, fim: 10, cor: ESCALA[4] },
  ]);
});

test("une classes repetidas e mantém as pontas da escala", () => {
  const classes = classificar([5, 5, 5, 9]);
  expect(classes.map((classe) => [classe.inicio, classe.fim])).toEqual([
    [5, 5],
    [9, 9],
  ]);
  expect(classes.map((classe) => classe.cor)).toEqual([ESCALA[0], ESCALA[4]]);
  expect(classificar([null, null])).toEqual([]);
});

test("dá a cor da classe de cada taxa e a cor de sem dado aos nulos", () => {
  const classes = classificar([1, 2, 3, 4, 5, 6, 7, 8, 9, 10]);
  expect(corDoValor(1, classes)).toBe(ESCALA[0]);
  expect(corDoValor(6, classes)).toBe(ESCALA[2]);
  expect(corDoValor(10, classes)).toBe(ESCALA[4]);
  expect(corDoValor(null, classes)).toBe(COR_SEM_DADO);
});

test("calcula o retângulo da malha em latitude e longitude", () => {
  expect(limitesDaMalha(malha)).toEqual([
    [-23, -70],
    [-9, -41],
  ]);
});
