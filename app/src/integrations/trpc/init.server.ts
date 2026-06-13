import { createTRPCInstance } from "@arata-ai/applications-core/libs/trpc/init";
import type { Context } from "../context";

/**
 * Server-side context for tRPC procedures
 * Includes Database API client with automatic Azure AD token injection
 *
 * ⚠️ This context is ONLY available on the server side
 */

const trpc = createTRPCInstance<Context>();

export const appRouter = trpc.router;
export const baseProcedure = trpc.baseProcedure;
export const authedProcedure = trpc.authedProcedure;
export const adminProcedure = trpc.adminProcedure;

export type AppRouter = typeof appRouter;
