import { createAPIClient } from "@arata-ai/applications-core/libs/api-client";
import { env } from "@/env";
import { fileTokenService } from "./services/file-token-service";

/**
 * File Service API Client
 *
 * Type-safe client for making requests to the File Service API.
 * Built on ky with automatic Azure AD Bearer token injection.
 * Only runs on the backend - token is never exposed to frontend.
 */
export const fileAPI = createAPIClient({
  baseUrl: env.FILE_SERVICE_URL,
  tokenProvider: fileTokenService,
  clientName: "FileAPIClient",
});

export type FileAPIClient = typeof fileAPI;
