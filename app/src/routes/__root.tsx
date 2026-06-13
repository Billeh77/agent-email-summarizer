import { PageNotFound } from "@arata-ai/applications-core/ui/components/page-not-found";
import {
  createRootRouteWithContext,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";
import { getUserFn } from "@/functions/auth";
import { getPublicConfigFn } from "@/functions/config";
import type { RouterContext } from "@/router";
import appCss from "../styles.css?url";

export const Route = createRootRouteWithContext<RouterContext>()({
  beforeLoad: async () => {
    // This runs on the server (SSR) and client (Navigation)
    const [user, config] = await Promise.all([
      getUserFn(),
      getPublicConfigFn(),
    ]);
    return { user, config };
  },
  head: () => ({
    meta: [
      {
        charSet: "utf-8",
      },
      {
        name: "viewport",
        content: "width=device-width, initial-scale=1",
      },
      {
        title: "Arata AI",
      },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
    ],
  }),
  notFoundComponent: PageNotFound,
  shellComponent: RootDocument,
});

function RootDocument({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}
