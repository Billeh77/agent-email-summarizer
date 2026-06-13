import { createTRPCReact } from "@arata-ai/applications-core/libs/trpc/react";
import type { TRPCRouter } from "@/integrations/trpc/router.server";

export const { TRPCProvider, useTRPC } = createTRPCReact<TRPCRouter>();
