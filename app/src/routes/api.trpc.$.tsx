import { createFileRoute } from "@tanstack/react-router";
import { fetchRequestHandler } from "@trpc/server/adapters/fetch";
import { createContext } from "@/integrations/context";
import { trpcRouter } from "@/integrations/trpc/router.server";

// Base path for gateway routing - only needed in production (non-dev)
const basePath = import.meta.env.DEV
  ? ""
  : import.meta.env.VITE_BASE_PATH || "/agents/email-summarizer";

function handler({ request }: { request: Request }) {
  return fetchRequestHandler({
    req: request,
    router: trpcRouter,
    endpoint: `${basePath}/api/trpc`,
    createContext,
  });
}

export const Route = createFileRoute("/api/trpc/$")({
  server: {
    handlers: {
      GET: handler,
      POST: handler,
    },
  },
});
