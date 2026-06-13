import type { TRPCRouterRecord } from "@trpc/server";
import z from "zod";
import { authedProcedure } from "../init.server";

const workflowResponseParser = z.object({
  workflowId: z.string(),
  status: z.string(),
});

export default {
  trigger: authedProcedure
    .input(
      z.object({
        workflowName: z.string(),
        payload: z.record(z.unknown()).optional(),
      }),
    )
    .mutation(async ({ ctx, input }) => {
      const response = await ctx.databaseAPI.post("/v1/workflows/trigger", {
        workflow_name: input.workflowName,
        payload: input.payload ?? {},
      });
      return workflowResponseParser.parse(response);
    }),
} satisfies TRPCRouterRecord;
