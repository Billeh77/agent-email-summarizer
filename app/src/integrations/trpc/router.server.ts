import { appRouter } from "./init.server";
import agentsRouter from "./routers/agents";
import workflowsRouter from "./routers/workflows";
import statsRouter from "./routers/stats";
import emailsRouter from "./routers/emails";

export const trpcRouter = appRouter({
  agents: agentsRouter,
  workflows: workflowsRouter,
  stats: statsRouter,
  emails: emailsRouter,
});
export type TRPCRouter = typeof trpcRouter;
