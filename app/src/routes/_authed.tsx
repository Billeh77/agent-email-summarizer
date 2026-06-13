import { SidebarProvider, useSidebar } from "@arata-ai/applications-core/ui/primitives/sidebar";
import { createFileRoute, Outlet, redirect } from "@tanstack/react-router";
import { AppSidebar } from "@/components/app-sidebar";

export const Route = createFileRoute("/_authed")({
  beforeLoad: async ({ context, location }) => {
    if (!context.user) {
      throw redirect({
        href: `${context.config?.homeAppUrl}/login`,
        search: {
          redirect: location.href,
        },
      });
    }
  },
  component: AuthLayout,
});

function AuthLayoutContent() {
  const { state } = useSidebar();
  const isOpen = state === "expanded";

  return (
    <>
      <AppSidebar />
      <main
        className={`transition-all duration-300 ease-in-out w-full isolate ${
          isOpen ? "ml-64" : "ml-16"
        }`}
      >
        <Outlet />
      </main>
    </>
  );
}

function AuthLayout() {
  return (
    <SidebarProvider>
      <AuthLayoutContent />
    </SidebarProvider>
  );
}
