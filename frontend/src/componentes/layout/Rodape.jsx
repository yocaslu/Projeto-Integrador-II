// Fontes dos dados (RNF12) e link para o código-fonte sob a AGPL-3.0 (RNF13).
// __REPOSITORIO_URL__ é definido pelo Vite (vite.config.js) e pelo Jest (package.json).
/* global __REPOSITORIO_URL__ */

export default function Rodape() {
  return (
    <footer className="rodape">
      <p>
        Fontes: Fórum Brasileiro de Segurança Pública (FBSP), Anuário Brasileiro de Segurança
        Pública 2026; IBGE, estimativas e projeções da população, usadas como denominador das
        taxas.
      </p>
      <p>
        Software livre sob a licença GNU AGPL-3.0. <a href={__REPOSITORIO_URL__}>Código-fonte</a>
      </p>
    </footer>
  );
}
