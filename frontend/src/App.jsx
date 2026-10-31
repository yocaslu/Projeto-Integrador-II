import Painel from "./paginas/Painel.jsx";
import Rodape from "./componentes/layout/Rodape.jsx";
import useTema from "./hooks/useTema.js";

export default function App() {
  const { tema, alternar } = useTema();

  return (
    <>
      <a className="pular-conteudo" href="#conteudo">
        Pular para o conteúdo
      </a>
      <header className="cabecalho">
        <h1>Painel do Anuário Brasileiro de Segurança Pública</h1>
        <button type="button" className="botao-tema" onClick={alternar}>
          {tema === "escuro" ? "Usar tema claro" : "Usar tema escuro"}
        </button>
      </header>
      <main id="conteudo">
        <Painel />
      </main>
      <Rodape />
    </>
  );
}
