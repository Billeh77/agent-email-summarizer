import { withTenantInjection } from "@arata-ai/applications-core/libs/api-client";
import type { AuthUser, User } from "@arata-ai/applications-core/libs/auth";
import { createServerFn } from "@tanstack/react-start";
import { env } from "@/env";
import { useAppSession } from "@/hooks/use-app-session";
import { databaseAPI } from "@/integrations/azure";
import { refreshAccessToken } from "@/lib/auth-refresh";

// Attempts to silently refresh the session using the stored refresh token.
// Returns true if successful, false if the refresh token is expired/missing.
export const reAuthFn = createServerFn({ method: "POST" }).handler(
	async (): Promise<boolean> => {
		const session = await useAppSession();
		const { refreshToken } = session.data;
		if (!refreshToken) return false;

		const newTokens = await refreshAccessToken(refreshToken);
		if (!newTokens) return false;

		await session.update({
			accessToken: newTokens.accessToken,
			refreshToken: newTokens.refreshToken,
		});
		return true;
	},
);

export const logoutFn = createServerFn({ method: "POST" }).handler(async () => {
	// 1. Clear the HTTP-only cookie
	const session = await useAppSession();
	await session.clear();

	const params = new URLSearchParams({
		client_id: env.AUTH0_CLIENT_ID,
		returnTo: `${env.HOME_APP_URL}/login`,
	});

	const logoutUrl = `https://${env.AUTH0_DOMAIN}/v2/logout?${params.toString()}`;

	// 3. Return the URL to the client
	return { logoutUrl };
});

// 3. Get User (Used by Root Route)
export const getUserFn = createServerFn({ method: "GET" }).handler(
	async (): Promise<AuthUser | null> => {
		const session = await useAppSession();
		if (!session.data.userId) return null;

		// Get AuthUser from session
		const { accessToken, refreshToken, ...authUser } = session.data;

		// Fetch full user record from database using auth0_id
		try {
			const tenant = session.data.tenant;
			if (!tenant) {
				// If no tenant, just return the auth user
				return authUser as AuthUser;
			}

			const tenantAwareDatabaseAPI = withTenantInjection(databaseAPI, tenant);
			const dbUser = await tenantAwareDatabaseAPI.get<User>(
				`/v1/users/by-auth0-id/${authUser.userId}`,
			);

			// Verify the auth0_id matches
			if (dbUser.auth0_id !== authUser.userId) {
				// Mismatch - security concern, just return auth user
				return authUser as AuthUser;
			}

			// Return combined user object with both auth and database info
			// Explicitly construct to ensure required fields are present
			return {
				...dbUser,
				userId: authUser.userId as string, // Already checked session.data.userId above
				email: authUser.email as string,
				roles: authUser.roles as AuthUser["roles"],
				name: authUser.name ?? dbUser.name ?? undefined,
				picture: authUser.picture ?? dbUser.picture ?? undefined,
				tenant: authUser.tenant,
			};
		} catch (_error) {
			// If database fetch fails, just return the auth user
			return authUser as AuthUser;
		}
	},
);
