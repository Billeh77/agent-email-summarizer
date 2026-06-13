import { processAuthMiddleware } from "@arata-ai/applications-core/libs/auth";
import { createMiddleware } from "@tanstack/react-start";
import { useAppSession } from "@/hooks/use-app-session";
import { refreshAccessToken } from "@/lib/auth-refresh";
import { authVerifier } from "@/lib/auth-validation";

export const authMiddleware = createMiddleware().server(async ({ next }) => {
  const session = await useAppSession();
  const user = await processAuthMiddleware(session, {
    refreshAccessToken,
    authVerifier,
  });

  return next({
    context: {
      user,
    },
  });
});
