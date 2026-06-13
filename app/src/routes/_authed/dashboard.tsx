import { useQuery } from "@tanstack/react-query";
import { createFileRoute, Link } from "@tanstack/react-router";

import { MAXIMUM_VIEW_PORT_WIDTH } from "@arata-ai/applications-core/libs/global-constants";
import { H2, P } from "@arata-ai/applications-core/ui/components/typography";

import { useTRPC } from "@/integrations/trpc/react";

export const Route = createFileRoute("/_authed/dashboard")({
  component: RouteComponent,
});

function StatCard({
  label,
  value,
  color,
  loading,
}: {
  label: string;
  value: number;
  color: string;
  loading: boolean;
}) {
  return (
    <div
      className="flex flex-col gap-2 rounded-xl p-6 text-white shadow-md flex-1 min-w-[180px]"
      style={{ backgroundColor: color }}
    >
      <P className="text-sm font-medium opacity-80 text-white">{label}</P>
      {loading ? (
        <div className="h-10 w-16 animate-pulse rounded bg-white/30" />
      ) : (
        <span className="text-4xl font-bold">{value}</span>
      )}
    </div>
  );
}

function RouteComponent() {
  const containerStyle = { maxWidth: MAXIMUM_VIEW_PORT_WIDTH };
  const trpc = useTRPC();

  const { data, isPending } = useQuery(trpc.stats.overview.queryOptions());

  return (
    <div className="flex flex-col gap-8 p-6 w-full" style={containerStyle}>
      <div className="space-y-2">
        <H2>Dashboard</H2>
        <P className="text-muted-foreground">
          Overview of your Email Summarizer agent activity.
        </P>
      </div>

      <div className="flex gap-4 flex-wrap">
        <StatCard
          label="Emails Received"
          value={data?.emailsReceived ?? 0}
          color="#7c6af7"
          loading={isPending}
        />
        <StatCard
          label="Summaries Generated"
          value={data?.summariesGenerated ?? 0}
          color="#22c55e"
          loading={isPending}
        />
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <p className="text-base font-semibold">Recent Emails</p>
          <Link
            to="/email-history"
            className="text-sm text-blue-600 hover:underline"
          >
            View all →
          </Link>
        </div>
        <P className="text-muted-foreground text-sm">
          See the full history of processed emails and their summaries in{" "}
          <Link to="/email-history" className="text-blue-600 hover:underline">
            Email History
          </Link>
          .
        </P>
      </div>
    </div>
  );
}
