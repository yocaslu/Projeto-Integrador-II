import Painel from "./paginas/Painel.jsx";
import Rodape from "./componentes/layout/Rodape.jsx";

export default function App() {
  return (
    <>
      <a className="pular-conteudo" href="#conteudo">
        Pular para o conteúdo
      </a>
      <header className="cabecalho">
        <h1>Painel do Anuário Brasileiro de Segurança Pública</h1>
      </header>
      <main id="conteudo">
        <Painel />
      </main>
      <Rodape />
    </>
  );
}
