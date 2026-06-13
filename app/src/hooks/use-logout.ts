import { createLogger } from "@arata-ai/applications-core/libs/logger";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import { useServerFn } from "@tanstack/react-start";
import { env } from "@/env";
import { logoutFn } from "../functions/auth";

const logger = createLogger("auth.logout");

export function useLogout() {
  const logoutServer = useServerFn(logoutFn);
  const router = useRouter();
  const queryClient = useQueryClient();

  const logout = async () => {
    try {
      // 1. Clear cookie on server
      const { logoutUrl } = await logoutServer();

      // 2. Clear Client-side Cache
      queryClient.clear();
      router.invalidate();

      // 3. Hard Redirect to Auth0
      window.location.href = logoutUrl;
    } catch (error) {
      logger.error("Logout failed", {
        error: error instanceof Error ? error.message : String(error),
      });
      // Fallback: just go to login if server fails
      router.navigate({ href: `${env.HOME_APP_URL}/login` });
    }
  };

  return { logout };
}
