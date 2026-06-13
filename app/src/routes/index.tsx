import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";

export const Route = createFileRoute("/")({
  component: RouteComponent,
  beforeLoad: async ({ context }) => {
    const { user, config } = context;
    if (user) {
      throw redirect({
        to: "/dashboard",
        replace: true,
      });
    }
    throw redirect({
      href: `${config?.homeAppUrl}/login`,
      replace: true,
    });
  },
});

function RouteComponent() {
  return <Outlet />;
}
