import { createServerFn } from "@tanstack/react-start";
import { env } from "@/env";

/**
 * Public configuration that can be safely exposed to the client.
 * DO NOT include secrets like CLIENT_SECRET, SESSION_SECRET, etc.
 */
export interface PublicConfig {
  serverUrl: string;
  appUrl: string;
  homeAppUrl: string;
}

/**
 * Server function that returns public configuration to the UI.
 * This allows runtime configuration without baking values into the build.
 */
export const getPublicConfigFn = createServerFn({ method: "GET" }).handler(
  async (): Promise<PublicConfig> => {
    return {
      serverUrl: env.EMAIL_SUMMARIZER_APP_URL,
      appUrl: env.EMAIL_SUMMARIZER_APP_URL,
      homeAppUrl: env.HOME_APP_URL ?? "/",
    };
  },
);
