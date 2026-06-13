import { AzureTokenService } from "@arata-ai/applications-core/libs/api-client";
import { env } from "@/env";

/**
 * Azure Token Service
 *
 * This service manages Azure AD tokens for authenticating with the Database API.
 * - Fetches credentials from Azure Key Vault
 * - Generates access tokens using client credentials flow
 * - Automatically refreshes tokens before expiration
 * - Runs only on the backend (server-side only)
 */
export const databaseTokenService = new AzureTokenService({
  keyVaultUri: env.AZURE_KEYVAULT_URI,
  callerService: env.AZURE_CALLER_SERVICE,
  audienceService: env.AZURE_DB_SERVICE,
  tenantId: env.AZURE_TENANT_ID,
  clientId: env.AZURE_CLIENT_ID,
  clientSecret: env.AZURE_CLIENT_SECRET,
});
