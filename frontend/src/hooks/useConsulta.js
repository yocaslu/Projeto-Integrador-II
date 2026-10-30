import { useEffect, useState } from "react";

// Executa uma consulta à API sempre que as dependências mudam e cancela a anterior,
// para que uma resposta atrasada não sobrescreva a do filtro atual.
// Com ativo = false, a consulta espera (por exemplo, até os metadados chegarem).
export default function useConsulta(consulta, dependencias, ativo = true) {
  const [estado, setEstado] = useState({ dados: null, carregando: ativo, erro: null });

  useEffect(() => {
    if (!ativo) return undefined;
    const controle = new AbortController();
    setEstado((anterior) => ({ ...anterior, carregando: true, erro: null }));
    consulta({ signal: controle.signal })
      .then((dados) => setEstado({ dados, carregando: false, erro: null }))
      .catch((erro) => {
        if (erro.name === "AbortError") return;
        setEstado({ dados: null, carregando: false, erro });
      });
    return () => controle.abort();
    // As dependências são as do chamador, como em useEffect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...dependencias, ativo]);

  return estado;
}
