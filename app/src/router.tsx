import type { AuthUser } from "@arata-ai/applications-core/libs/auth";
import type { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { setupRouterSsrQueryIntegration } from "@tanstack/react-router-ssr-query";
import type { TRPCOptionsProxy } from "@trpc/tanstack-react-query";
import type { PublicConfig } from "./functions/config";
import * as TanstackQuery from "./integrations/tanstack-query/root-provider";
import type { TRPCRouter } from "./integrations/trpc/router.server";
// Import the generated route tree
import { routeTree } from "./routeTree.gen";

export interface RouterContext {
  queryClient: QueryClient;
  trpc: TRPCOptionsProxy<TRPCRouter>;
  user?: AuthUser | null;
  config?: PublicConfig;
}

// Create a new router instance
export const getRouter = () => {
  const rqContext = TanstackQuery.getContext();

  const router = createRouter({
    routeTree,
    context: { ...rqContext },
    defaultPreload: false,
    Wrap: (props: { children: React.ReactNode }) => {
      return (
        <TanstackQuery.Provider {...rqContext}>
          {props.children}
        </TanstackQuery.Provider>
      );
    },
  });

  setupRouterSsrQueryIntegration({
    router,
    queryClient: rqContext.queryClient,
  });

  return router;
};
