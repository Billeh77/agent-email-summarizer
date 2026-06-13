import type { AuthSession } from "@arata-ai/applications-core/libs/auth";
import { useSession } from "@tanstack/react-start/server";
import { env } from "@/env";

export function useAppSession() {
  // Behind Azure App Gateway with HTTPS termination
  const isSecure =
    env.EMAIL_SUMMARIZER_APP_URL?.startsWith("https://") ||
    process.env.NODE_ENV === "production";

  return useSession<AuthSession>({
    name: "auth_session", // Cookie name
    password: env.AUTH0_SESSION_SECRET,
    cookie: {
      secure: isSecure,
      sameSite: "lax",
      path: "/", // Ensure cookie is accessible across all paths behind App Gateway
      httpOnly: true, // Critical for security (JS cannot read this)
      maxAge: 60 * 60 * 24 * 7, // 7 days
    },
  });
}
