import {
  AppSidebar as AppSidebarBase,
  IconName,
  type NavGroup,
} from "@arata-ai/applications-core/ui/components/app-sidebar";
import { useSidebar } from "@arata-ai/applications-core/ui/primitives/sidebar";
import { Link, useRouterState } from "@tanstack/react-router";
import { useConfig } from "@/hooks/use-config";
import { UserProfile } from "./user-profile";

const navigationConfig: NavGroup[] = [
  {
    label: "Navigation",
    items: [
      {
        id: "dashboard",
        title: "Dashboard",
        href: "/dashboard",
        icon: IconName.Home,
      },
      {
        id: "email-history",
        title: "Email History",
        href: "/email-history",
        icon: IconName.Mail,
      },
    ],
  },
];

export function AppSidebar() {
  const routerState = useRouterState();
  const { data: config } = useConfig();
  const currentPath = routerState.location.pathname;
  const { state } = useSidebar();
  const isOpen = state === "expanded";

  return (
    <AppSidebarBase
      navigation={navigationConfig}
      header={{
        logoAlt: "Arata Logo",
        logoHref: config?.homeAppUrl ?? "/",
        title: "Email Summarizer",
        subtitle: "Workspace",
      }}
      footer={<UserProfile isExpanded={isOpen} />}
      LinkComponent={Link}
      isItemActive={(item) => currentPath === item.href}
    />
  );
}
