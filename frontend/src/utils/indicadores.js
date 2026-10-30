// A árvore de indicadores de /metadados/ vira uma lista plana, na ordem da hierarquia,
// com o nível de cada indicador para a indentação no seletor.
export function achatarIndicadores(arvore, nivel = 0) {
  return arvore.flatMap((indicador) => [
    {
      slug: indicador.slug,
      nome: indicador.nome,
      nivel,
      base_taxa: indicador.base_taxa,
      possui_registros: indicador.possui_registros,
      anos: indicador.anos,
    },
    ...achatarIndicadores(indicador.subtipos ?? [], nivel + 1),
  ]);
}
