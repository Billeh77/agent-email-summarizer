import { withTenantInjection } from "@arata-ai/applications-core/libs/api-client";
import { TRPCError } from "@trpc/server";
import { useAppSession } from "@/hooks/use-app-session";
import { databaseAPI, fileAPI } from "@/integrations/azure";

/**
 * Server-side context for tRPC procedures
 * Includes API clients with automatic Azure AD token injection
 *
 * ⚠️ This context is ONLY available on the server side
 */

/**
 * Creates tenant-aware API client wrappers that automatically inject tenant from user context
 */
function createTenantAwareClients(tenant: string) {
  const tenantAwareDatabaseAPI = withTenantInjection(databaseAPI, tenant);


  const tenantAwareFileAPI = withTenantInjection(fileAPI, tenant);


  return {
    databaseAPI: tenantAwareDatabaseAPI,


    fileAPI: tenantAwareFileAPI,

  };
}

export async function createContext() {
  const session = await useAppSession();
  const user = session.data;

  // Rely on auth middleware to have already validated and refreshed the token
  if (!user?.accessToken || !user?.tenant) {
    throw new TRPCError({ code: "UNAUTHORIZED" });
  }

  // Create tenant-aware API clients if user has tenant
  const apiClients = createTenantAwareClients(user.tenant);

  return {
    user,
    ...apiClients,
  };
}

export type Context = Awaited<ReturnType<typeof createContext>>;
