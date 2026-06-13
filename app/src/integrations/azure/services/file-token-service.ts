import { AzureTokenService } from "@arata-ai/applications-core/libs/api-client";
import { env } from "@/env";

/**
 * Azure Token Service for File Service API
 *
 * Manages Azure AD tokens for authenticating with the File service.
 * Same pattern as db-token-service but with File service-specific audience.
 */
export const fileTokenService = new AzureTokenService({
  keyVaultUri: env.AZURE_KEYVAULT_URI,
  callerService: env.AZURE_CALLER_SERVICE,
  audienceService: env.AZURE_FILE_SERVICE,
  tenantId: env.AZURE_TENANT_ID,
  clientId: env.AZURE_CLIENT_ID,
  clientSecret: env.AZURE_CLIENT_SECRET,
});
