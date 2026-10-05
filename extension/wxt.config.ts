import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "wxt";

export default defineConfig({
  zip: {
    name: "soundify-extension",
    artifactTemplate: "{{name}}-{{packageVersion}}-{{browser}}.zip",
    sourcesTemplate: "{{name}}-{{packageVersion}}-sources.zip",
    zipSources: true,
  },
  modules: ["@wxt-dev/auto-icons"],
  autoIcons: {
    baseIconPath: "assets/icon.svg",
    developmentIndicator: false,
  },
  manifest: {
    name: "soundify",
    description: "Send YouTube URLs to your soundify instance",
    homepage_url: "https://soundify.guillevc.dev",
    permissions: ["storage", "activeTab", "tabs"],
    browser_specific_settings: {
      gecko: {
        id: "soundify@guillevc.xyz",
        // @ts-expect-error -- not yet in WXT's type definitions
        data_collection_permissions: {
          required: ["none"],
          optional: [],
        },
      },
    },
  },
  vite: () => ({
    plugins: [tailwindcss()],
  }),
});
