import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const REPOSITORIO_URL =
  process.env.VITE_REPOSITORIO_URL ?? "https://github.com/yocaslu/projeto-integrador-ii";

// No desenvolvimento, /api é repassado ao backend, o que dispensa CORS.
// Em produção, o Traefik faz o mesmo roteamento no domínio público.
export default defineConfig({
  plugins: [react()],
  define: {
    __REPOSITORIO_URL__: JSON.stringify(REPOSITORIO_URL),
  },
  server: {
    proxy: {
      "/api": process.env.VITE_PROXY_API ?? "http://backend:8000",
    },
  },
});
