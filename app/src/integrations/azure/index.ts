/**
 * Azure Integration Module
 *
 * Provides backend-only Azure services for:
 * - Azure AD token management with auto-refresh
 * - Database API client with automatic token injection
 *
 * ⚠️ SECURITY NOTICE:
 * These services MUST only be used in server-side code (tRPC routers, loaders, etc.)
 * Never import or expose these to client-side code to prevent token leakage
 */

export type {
  APIClient,
  TokenProvider,
} from "@arata-ai/applications-core/libs/api-client";
export { type DatabaseAPIClient, databaseAPI } from "./database-client";
export { databaseTokenService } from "./services/db-token-service";


export { type FileAPIClient, fileAPI } from "./file-client";
export { fileTokenService } from "./services/file-token-service";

