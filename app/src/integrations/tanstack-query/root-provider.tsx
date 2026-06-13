import { createAgentRegistration } from "@arata-ai/applications-core/libs/agent-registration";
import { createReAuthLink } from "@arata-ai/applications-core/libs/auth";
import { QueryClient } from "@tanstack/react-query";
import { createIsomorphicFn } from "@tanstack/react-start";
import {
  createTRPCClient,
  httpBatchLink,
  httpBatchStreamLink,
  splitLink,
} from "@trpc/client";
import { createTRPCOptionsProxy } from "@trpc/tanstack-react-query";
import superjson from "superjson";
import { env } from "@/env";
import { reAuthFn } from "@/functions/auth";
import { getPublicConfigFn } from "@/functions/config";
import { TRPCProvider } from "@/integrations/trpc/react";
import type { TRPCRouter } from "@/integrations/trpc/router.server";

/**
 * Forward browser cookies during SSR so tRPC server-to-server calls
 * include the auth_session cookie.
 */
const getSSRHeaders = createIsomorphicFn()
  .client(async () => ({}))
  .server(async () => {
    const { getRequestHeaders } = await import("@tanstack/react-start/server");
    const cookie = getRequestHeaders().get("cookie");
    return cookie ? { cookie } : {};
  });

const AGENT_NAME = "email-summarizer";

// Base path for gateway routing - only needed in production (non-dev)
const basePath = import.meta.env.DEV
  ? ""
  : import.meta.env.VITE_BASE_PATH || "/agents/email-summarizer";

function getUrl() {
  const base = (() => {
    if (typeof window !== "undefined") return basePath;
    return env.SERVER_URL;
  })();
  return `${base}/api/trpc`;
}

const reAuthLink = createReAuthLink<TRPCRouter>({
  reAuthFn,
  getLoginUrl: async (currentHref) => {
    const config = await getPublicConfigFn();
    return `${config.homeAppUrl}/login?redirect=${encodeURIComponent(currentHref)}`;
  },
});

// Create a lazy trpcClient getter to break circular dependency
let _trpcClient: ReturnType<typeof createTRPCClient<TRPCRouter>> | null = null;

function getTrpcClient() {
  if (!_trpcClient) {
    throw new Error("trpcClient not initialized yet");
  }
  return _trpcClient;
}

// Create agent registration helpers - uses lazy getter for trpcClient
const { registrationLink, triggerRegistration } = createAgentRegistration({
  agentName: AGENT_NAME,
  getAgent: () => getTrpcClient().agents.get.query(),
  registerAgent: () => getTrpcClient().agents.registerByName.mutate(),
  getHomeAppUrl: async () => (await getPublicConfigFn()).homeAppUrl,
});

// Now create the actual trpcClient with the registration link
const trpcClientInstance = createTRPCClient<TRPCRouter>({
  links: [
    // Registration link MUST be first - blocks non-agent calls until registered
    registrationLink,
    reAuthLink,
    splitLink({
      // Use streaming for file operations (large payloads benefit from streaming)
      condition: (op) => op.path.startsWith("files."),
      true: httpBatchStreamLink({
        transformer: superjson,
        url: getUrl(),
        headers: getSSRHeaders,
      }),
      // Use non-streaming for database operations (easier to debug in Network tab)
      false: httpBatchLink({
        transformer: superjson,
        url: getUrl(),
        headers: getSSRHeaders,
      }),
    }),
  ],
});

_trpcClient = trpcClientInstance;
export const trpcClient = trpcClientInstance;

export function getContext() {
  const queryClient = new QueryClient({
    defaultOptions: {
      dehydrate: { serializeData: superjson.serialize },
      hydrate: { deserializeData: superjson.deserialize },
    },
  });

  const serverHelpers = createTRPCOptionsProxy({
    client: trpcClient,
    queryClient: queryClient,
  });

  const context = {
    queryClient,
    trpc: serverHelpers,
  };

  return context;
}

export function Provider({
  children,
  queryClient,
}: {
  children: React.ReactNode;
  queryClient: QueryClient;
}) {
  // Register agent once on first client-side mount
  triggerRegistration();

  return (
    <TRPCProvider trpcClient={trpcClient} queryClient={queryClient}>
      {children}
    </TRPCProvider>
  );
}
