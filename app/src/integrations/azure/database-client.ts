import { createAPIClient } from "@arata-ai/applications-core/libs/api-client";
import { env } from "@/env";
import { databaseTokenService } from "./services/db-token-service";

/**
 * Database API Client
 *
 * Type-safe client for making requests to the Database API.
 * Built on ky with automatic Azure AD Bearer token injection.
 * Only runs on the backend - token is never exposed to frontend.
 */
export const databaseAPI = createAPIClient({
  baseUrl: env.ARATA_DB_URL,
  tokenProvider: databaseTokenService,
  clientName: "DatabaseAPIClient",
});

export type DatabaseAPIClient = typeof databaseAPI;
