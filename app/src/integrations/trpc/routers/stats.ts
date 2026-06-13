import type { TRPCRouterRecord } from "@trpc/server";
import z from "zod";
import { authedProcedure } from "../init.server";

const AGENT_NAME = "email-summarizer";

const _agentParser = z.object({ id: z.string() });
const _summaryListParser = z.array(z.object({ id: z.string() }));

export default {
  overview: authedProcedure.query(async ({ ctx }) => {
    const agent = await ctx.databaseAPI.get(`/v1/agents/name/${AGENT_NAME}`);
    const { id: agentId } = _agentParser.parse(agent);

    const summaries = await ctx.databaseAPI.get(
      `/v1/summaries?summary_type=DETAILED&agent_id=${agentId}`,
    );
    const summaryList = _summaryListParser.parse(summaries);

    return {
      emailsReceived: summaryList.length,
      summariesGenerated: summaryList.length,
    };
  }),
} satisfies TRPCRouterRecord;
