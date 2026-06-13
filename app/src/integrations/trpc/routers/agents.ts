import type { TRPCRouterRecord } from "@trpc/server";
import z from "zod";
import { authedProcedure } from "../init.server";

// Agent parser matching the backend Agent model
const _agentParser = z.object({
  id: z.string(),
  name: z.string(),
  principals: z.array(z.string()),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
});

const AGENT_NAME = "email-summarizer";

export type Agent = z.infer<typeof _agentParser>;

export default {
  registerByName: authedProcedure.mutation(async ({ ctx }) => {
    const response = await ctx.databaseAPI.put(
      `/v1/agents/name/${AGENT_NAME}`, // hardcoded on purpose
    );
    return _agentParser.parse(response);
  }),
  get: authedProcedure.query(async ({ ctx }) => {
    const response = await ctx.databaseAPI.get(`/v1/agents/name/${AGENT_NAME}`); // hardcoded on purpose
    return _agentParser.parse(response);
  }),
} satisfies TRPCRouterRecord;
