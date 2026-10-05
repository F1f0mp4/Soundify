import { defineConfig } from "@playwright/test";
import path from "path";

const ROOT = path.resolve(__dirname, "..");

function serverEnv(name: string, extra: Record<string, string> = {}) {
  return {
    SOUNDIFY_ROOT: ROOT,
    SOUNDIFY_DATA: `/tmp/soundify-e2e-${name}/data`,
    SOUNDIFY_CONFIG: `/tmp/soundify-e2e-${name}/config`,
    SOUNDIFY_SCHEDULER_ENABLED: "false",
    SOUNDIFY_LOG_LEVEL: "WARNING",
    ...extra,
  };
}

export default defineConfig({
  testDir: "./tests",
  timeout: 15_000,
  retries: 0,
  fullyParallel: false,
  use: {
    headless: true,
  },
  projects: [
    {
      name: "default",
      use: { baseURL: "http://127.0.0.1:8900" },
    },
    {
      name: "subfolder",
      use: { baseURL: "http://127.0.0.1:8901/soundify/" },
    },
  ],
  webServer: [
    {
      command: `uv run --package soundify-api uvicorn soundify_api.api.app:app --host 127.0.0.1 --port 8900`,
      url: "http://127.0.0.1:8900/api/health",
      reuseExistingServer: false,
      timeout: 30_000,
      env: serverEnv("default"),
    },
    {
      command: `uv run --package soundify-api uvicorn soundify_api.api.app:app --host 127.0.0.1 --port 8901`,
      url: "http://127.0.0.1:8901/soundify/api/health",
      reuseExistingServer: false,
      timeout: 30_000,
      env: serverEnv("subfolder", { SOUNDIFY_BASE_PATH: "/soundify" }),
    },
  ],
});
