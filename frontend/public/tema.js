// Aplica o tema antes da primeira pintura, para a página não piscar em claro. Fica em arquivo
// próprio porque a política de segurança de produção pode não aceitar script em linha.
(function () {
  var salvo = null;
  try {
    salvo = localStorage.getItem("tema");
  } catch (erro) {
    // Sem acesso ao armazenamento (navegação privada restrita): vale a preferência do sistema.
  }
  var escuro = salvo ? salvo === "escuro" : matchMedia("(prefers-color-scheme: dark)").matches;
  document.documentElement.dataset.tema = escuro ? "escuro" : "claro";
})();
