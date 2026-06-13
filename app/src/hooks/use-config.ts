import { useQuery } from "@tanstack/react-query";
import { getPublicConfigFn, type PublicConfig } from "@/functions/config";

/**
 * Hook to access public configuration in client components.
 */
export function useConfig() {
  return useQuery<PublicConfig>({
    queryKey: ["publicConfig"],
    queryFn: () => getPublicConfigFn(),
    staleTime: Number.POSITIVE_INFINITY, // Config doesn't change at runtime
  });
}
