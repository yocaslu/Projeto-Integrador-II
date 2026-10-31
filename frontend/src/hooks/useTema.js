import { useEffect, useState } from "react";

const CHAVE = "tema";

function salvo() {
  try {
    return localStorage.getItem(CHAVE);
  } catch {
    return null;
  }
}

function doSistema() {
  return window.matchMedia?.("(prefers-color-scheme: dark)").matches ? "escuro" : "claro";
}

// Tema da página (public/tema.js aplica o inicial). A escolha da pessoa fica salva; sem escolha,
// o tema acompanha o sistema.
export default function useTema() {
  const [tema, setTema] = useState(
    () => document.documentElement.dataset.tema ?? salvo() ?? doSistema(),
  );

  useEffect(() => {
    document.documentElement.dataset.tema = tema;
  }, [tema]);

  useEffect(() => {
    const preferencia = window.matchMedia?.("(prefers-color-scheme: dark)");
    if (!preferencia) return undefined;
    const aoMudar = () => {
      if (!salvo()) setTema(doSistema());
    };
    preferencia.addEventListener("change", aoMudar);
    return () => preferencia.removeEventListener("change", aoMudar);
  }, []);

  function alternar() {
    const novo = tema === "escuro" ? "claro" : "escuro";
    try {
      localStorage.setItem(CHAVE, novo);
    } catch {
      // Sem armazenamento, o tema vale até recarregar a página.
    }
    setTema(novo);
  }

  return { tema, alternar };
}
