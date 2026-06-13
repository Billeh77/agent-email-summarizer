import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";

import { MAXIMUM_VIEW_PORT_WIDTH } from "@arata-ai/applications-core/libs/global-constants";
import { H2, P } from "@arata-ai/applications-core/ui/components/typography";
import { Button } from "@arata-ai/applications-core/ui/primitives/button";

import { useTRPC } from "@/integrations/trpc/react";
import type { EmailRow } from "@/integrations/trpc/routers/emails";

export const Route = createFileRoute("/_authed/email-history")({
  component: RouteComponent,
});

const PAGE_SIZE = 20;

function formatDate(date: Date | null | undefined): string {
  if (!date) return "—";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date instanceof Date ? date : new Date(date));
}

function SummaryModal({
  row,
  onClose,
}: {
  row: EmailRow;
  onClose: () => void;
}) {
  const summary = row.summaryOutput;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[80vh] overflow-y-auto p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-lg font-semibold text-gray-900">{row.subject}</p>
            <P className="text-muted-foreground text-sm mt-1">
              From: {row.senderAddress} · {formatDate(row.receivedAt)}
            </P>
          </div>
          <button
            className="text-gray-400 hover:text-gray-700 text-xl leading-none flex-shrink-0"
            onClick={onClose}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {!summary ? (
          <P className="text-muted-foreground">Summary not available.</P>
        ) : (
          <>
            <section>
              <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                Overview
              </p>
              <P>{summary.overview}</P>
            </section>

            {summary.key_points.length > 0 && (
              <section>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                  Key Points
                </p>
                <ul className="list-disc list-inside space-y-1">
                  {summary.key_points.map((point, i) => (
                    <li key={i} className="text-sm text-gray-700">
                      {point}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {summary.attachment_highlights.length > 0 && (
              <section>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                  Attachment Highlights
                </p>
                <ul className="list-disc list-inside space-y-1">
                  {summary.attachment_highlights.map((item, i) => (
                    <li key={i} className="text-sm text-gray-700">
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {summary.action_items.length > 0 && (
              <section>
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 mb-1">
                  Action Items
                </p>
                <ul className="list-disc list-inside space-y-1">
                  {summary.action_items.map((item, i) => (
                    <li key={i} className="text-sm text-gray-700">
                      {item}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function RouteComponent() {
  const containerStyle = { maxWidth: MAXIMUM_VIEW_PORT_WIDTH };
  const [page, setPage] = useState(1);
  const [selectedRow, setSelectedRow] = useState<EmailRow | null>(null);
  const trpc = useTRPC();

  const { data, isPending } = useQuery(
    trpc.emails.list.queryOptions({ page, pageSize: PAGE_SIZE }),
  );

  const rows = data?.rows ?? [];
  const totalPages = data?.totalPages ?? 1;
  const totalCount = data?.totalCount ?? 0;

  return (
    <div className="flex flex-col gap-6 p-6 w-full" style={containerStyle}>
      {selectedRow && (
        <SummaryModal row={selectedRow} onClose={() => setSelectedRow(null)} />
      )}

      <div className="space-y-2">
        <H2>Email History</H2>
        <P className="text-muted-foreground">
          All emails processed by the summarizer agent.
        </P>
      </div>

      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left">
            <tr>
              <th className="px-4 py-3 font-semibold text-gray-600">
                Subject / Sender
              </th>
              <th className="px-4 py-3 font-semibold text-gray-600">
                Received
              </th>
              <th className="px-4 py-3 font-semibold text-gray-600 text-center">
                Attachments
              </th>
              <th className="px-4 py-3 font-semibold text-gray-600 text-center">
                Summary
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isPending ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>
                  <td className="px-4 py-3">
                    <div className="h-4 w-48 animate-pulse rounded bg-gray-200 mb-1" />
                    <div className="h-3 w-32 animate-pulse rounded bg-gray-100" />
                  </td>
                  <td className="px-4 py-3">
                    <div className="h-4 w-28 animate-pulse rounded bg-gray-200" />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="h-4 w-6 animate-pulse rounded bg-gray-200 mx-auto" />
                  </td>
                  <td className="px-4 py-3 text-center">
                    <div className="h-8 w-14 animate-pulse rounded bg-gray-200 mx-auto" />
                  </td>
                </tr>
              ))
            ) : rows.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="px-4 py-8 text-center text-muted-foreground"
                >
                  No emails processed yet.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.summaryId} className="hover:bg-gray-50 transition">
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900">
                      {row.subject}
                    </div>
                    <div className="text-xs text-gray-500 mt-0.5">
                      {row.senderAddress}
                    </div>
                  </td>
                  <td className="px-4 py-3 text-gray-600 whitespace-nowrap">
                    {formatDate(row.receivedAt)}
                  </td>
                  <td className="px-4 py-3 text-center text-gray-600">
                    {row.attachmentCount > 0 ? row.attachmentCount : "—"}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedRow(row)}
                    >
                      View
                    </Button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            Page {page} of {totalPages} ({totalCount} total)
          </span>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              ← Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next →
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
