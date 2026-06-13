import { arataCore } from "@arata-ai/applications-core/libs/vite-plugin";
import tailwindcss from "@tailwindcss/vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig } from "vite";
import viteTsConfigPaths from "vite-tsconfig-paths";

// Nitro preset - defaults to node-server for Docker/App Service deployments
const nitroPreset = process.env.NITRO_PRESET || "node-server";

// Base path for gateway routing - app is served at this path behind the gateway
// Gateway does NOT strip this path (APP_REWRITE=false), so both Vite and Nitro need it
const basePath =
  process.env.NODE_ENV === "development"
    ? ""
    : process.env.VITE_BASE_PATH || "/agents/email-summarizer";

const config = defineConfig({
  base: basePath,
  plugins: [
    arataCore(),
    nitro({
      preset: nitroPreset,
      baseURL: basePath,
    }),
    // this is the plugin that enables path aliases
    viteTsConfigPaths({
      projects: ["./tsconfig.json"],
    }),
    tailwindcss(),
    tanstackStart(),
    viteReact({
      babel: {
        plugins: ["babel-plugin-react-compiler"],
      },
    }),
  ],
});

export default config;
