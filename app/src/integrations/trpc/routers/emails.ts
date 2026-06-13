import type { TRPCRouterRecord } from "@trpc/server";
import z from "zod";
import { authedProcedure } from "../init.server";

const AGENT_NAME = "email-summarizer";

const _agentParser = z.object({ id: z.string() });

const _summaryParser = z.object({
  id: z.string(),
  doc_id: z.string(),
  summary_type: z.string(),
  text: z.string(),
  agent_id: z.string().nullable().optional(),
  created_at: z.coerce.date(),
  updated_at: z.coerce.date(),
});

const _emailParser = z.object({
  id: z.string(),
  subject: z.string().nullable().optional(),
  body: z.string().nullable().optional(),
  sender: z
    .object({ address: z.string() })
    .nullable()
    .optional(),
  from_: z
    .array(z.object({ address: z.string() }))
    .nullable()
    .optional(),
  received_at: z.coerce.date().nullable().optional(),
});

const _summaryOutputParser = z.object({
  overview: z.string(),
  key_points: z.array(z.string()),
  attachment_highlights: z.array(z.string()).default([]),
  action_items: z.array(z.string()).default([]),
});

export type EmailRow = {
  emailId: string;
  subject: string;
  senderAddress: string;
  receivedAt: Date | null;
  attachmentCount: number;
  summaryId: string;
  summaryCreatedAt: Date;
  summaryOutput: z.infer<typeof _summaryOutputParser> | null;
};

export default {
  list: authedProcedure
    .input(
      z.object({
        page: z.number().int().min(1).default(1),
        pageSize: z.number().int().min(1).max(50).default(20),
      }),
    )
    .query(async ({ ctx, input }) => {
      const agent = await ctx.databaseAPI.get(`/v1/agents/name/${AGENT_NAME}`);
      const { id: agentId } = _agentParser.parse(agent);

      const rawSummaries = await ctx.databaseAPI.get(
        `/v1/summaries?summary_type=DETAILED&agent_id=${agentId}`,
      );
      const allSummaries = z
        .array(_summaryParser)
        .parse(rawSummaries)
        .sort((a, b) => b.created_at.getTime() - a.created_at.getTime());

      const totalCount = allSummaries.length;
      const start = (input.page - 1) * input.pageSize;
      const pageSummaries = allSummaries.slice(start, start + input.pageSize);

      const rows: EmailRow[] = await Promise.all(
        pageSummaries.map(async (summary) => {
          let email: z.infer<typeof _emailParser> | null = null;
          try {
            const rawEmail = await ctx.databaseAPI.get(
              `/v1/emails-v2/${summary.doc_id}`,
            );
            email = _emailParser.parse(rawEmail);
          } catch {
            // email may have been deleted or access denied — skip gracefully
          }

          let summaryOutput: z.infer<typeof _summaryOutputParser> | null = null;
          try {
            summaryOutput = _summaryOutputParser.parse(
              JSON.parse(summary.text),
            );
          } catch {
            // malformed summary text — skip gracefully
          }

          const senderAddress =
            email?.from_?.[0]?.address ??
            email?.sender?.address ??
            "Unknown sender";

          return {
            emailId: summary.doc_id,
            subject: email?.subject ?? "(no subject)",
            senderAddress,
            receivedAt: email?.received_at ?? null,
            attachmentCount: summaryOutput?.attachment_highlights.length ?? 0,
            summaryId: summary.id,
            summaryCreatedAt: summary.created_at,
            summaryOutput,
          };
        }),
      );

      return {
        rows,
        totalCount,
        totalPages: Math.ceil(totalCount / input.pageSize),
        page: input.page,
        pageSize: input.pageSize,
      };
    }),
} satisfies TRPCRouterRecord;
