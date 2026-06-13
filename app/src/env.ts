import { createEnv } from "@t3-oss/env-core";
import { z } from "zod";

export const env = createEnv({
  server: {
    SERVER_URL: z.url().optional().default("http://localhost:3002"),
    ARATA_DB_URL: z.string().default("http://localhost:8000"),
    // Azure Key Vault configuration
    AZURE_KEYVAULT_URI: z.string(),
    AZURE_TENANT_ID: z.string(),
    AZURE_CALLER_SERVICE: z
      .string()
      .default("applications-email-summarizer"),
    AZURE_DB_SERVICE: z.string().default("db-service"),


    AZURE_FILE_SERVICE: z.string().default("file-service"),
    FILE_SERVICE_URL: z.string().default("https://localhost:8002"),

    // Service Principal credentials for Key Vault access (for Docker)
    AZURE_CLIENT_ID: z.string().optional(),
    AZURE_CLIENT_SECRET: z.string().optional(),
    AUTH0_DOMAIN: z.string(),
    AUTH0_CLIENT_ID: z.string(),
    AUTH0_CLIENT_SECRET: z.string(),
    AUTH0_SCOPE: z.string(),
    AUTH0_AUDIENCE: z.string().optional(),
    AUTH0_SESSION_SECRET: z.string(),
    EMAIL_SUMMARIZER_APP_URL: z.url().default("http://localhost:5174"),
    HOME_APP_URL: z.url().optional(),
  },

  /**
   * The prefix that client-side variables must have. This is enforced both at
   * a type-level and at runtime.
   */
  clientPrefix: "VITE_",

  /**
   * Notice: Adding UI variables causes issue with our build process.
   * It's better to add to the server, and then re-export it through getPublicConfigFn
   */
  client: {},

  /**
   * What object holds the environment variables at runtime. This is usually
   * `process.env` or `import.meta.env`.
   */
  runtimeEnv: {
    ...process.env,
    ...import.meta.env,
  },

  /**
   * By default, this library will feed the environment variables directly to
   * the Zod validator.
   *
   * This means that if you have an empty string for a value that is supposed
   * to be a number (e.g. `PORT=` in a ".env" file), Zod will incorrectly flag
   * it as a type mismatch violation. Additionally, if you have an empty string
   * for a value that is supposed to be a string with a default value (e.g.
   * `DOMAIN=` in an ".env" file), the default value will never be applied.
   *
   * In order to solve these issues, we recommend that all new projects
   * explicitly specify this option as true.
   */
  emptyStringAsUndefined: true,
});

export function getAuth0Audience(): string {
  return env.AUTH0_AUDIENCE ?? `https://${env.AUTH0_DOMAIN}/api/v2/`;
}
