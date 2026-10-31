// A árvore de indicadores de /metadados/ vira uma lista plana, na ordem da hierarquia,
// com o nível de cada indicador para a indentação no seletor.
export function achatarIndicadores(arvore, nivel = 0, pai = null) {
  return arvore.flatMap((indicador) => [
    {
      slug: indicador.slug,
      nome: indicador.nome,
      nivel,
      base_taxa: indicador.base_taxa,
      possui_registros: indicador.possui_registros,
      anos: indicador.anos,
      unidade_padrao: indicador.unidade_padrao,
      unidades: indicador.unidades ?? [],
      recortes: indicador.recortes ?? [],
      // Sem pai com registros (raízes e filhos de agrupador), a API não calcula a participação.
      tem_participacao: Boolean(pai?.possui_registros),
    },
    ...achatarIndicadores(indicador.subtipos ?? [], nivel + 1, indicador),
  ]);
}
