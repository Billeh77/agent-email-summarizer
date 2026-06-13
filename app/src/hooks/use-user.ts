import { Role } from "@arata-ai/applications-core/libs/auth";
import { getRouteApi } from "@tanstack/react-router";

// Access the root route where the context is defined
const rootRoute = getRouteApi("__root__");

export function useUser() {
  const { user } = rootRoute.useRouteContext();

  return {
    user,
    isAuthenticated: !!user,
    isAdmin: user?.roles.includes(Role.Admin),
  };
}
