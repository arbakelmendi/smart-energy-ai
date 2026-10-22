import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouterState } from "@tanstack/react-router";
import { ApiError } from "./api/client";
import { getCurrentUser, login, signup, logout, type AuthUser, type LoginRequest, type SignupRequest } from "./api/auth";

const KEY = ["auth", "me"] as const;
type AuthContext = {
  user: AuthUser | null; ready: boolean; error: Error | null;
  signIn: (body: LoginRequest) => Promise<void>;
  signUp: (body: SignupRequest) => Promise<void>;
  signOut: () => Promise<void>;
  retry: () => void;
};
const Context = createContext<AuthContext | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const client = useQueryClient();
  const [mounted, setMounted] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  useEffect(() => {
    // Retire the old demo key; its contents never establish authentication.
    try { window.localStorage.removeItem("sea-session"); } catch { /* Storage may be disabled. */ }
    setMounted(true);
  }, []);
  const query = useQuery({ queryKey: KEY, enabled: mounted, retry: false,
    staleTime: 0, refetchOnWindowFocus: true, refetchInterval: 60_000,
    queryFn: async ({ signal }) => {
      try { return await getCurrentUser(signal); }
      catch (error) { if (error instanceof ApiError && error.status === 401) return null; throw error; }
    },
  });
  useEffect(() => {
    if (mounted) void client.invalidateQueries({ queryKey: KEY });
  }, [pathname, mounted, client]);

  async function verifySession() {
    await client.cancelQueries({ queryKey: KEY });
    // The cookie must work: successful POST JSON alone does not establish UI auth.
    const user = await getCurrentUser();
    client.setQueryData(KEY, user);
  }
  async function signOut() {
    await logout();
    await client.cancelQueries();
    client.setQueryData(KEY, null);
    client.removeQueries({ predicate: (query) => query.queryKey[0] !== "auth" });
  }
  const value: AuthContext = {
    user: query.isError ? null : query.data ?? null,
    ready: mounted && !query.isPending,
    error: query.error,
    signIn: async (body) => { await login(body); await verifySession(); },
    signUp: async (body) => { await signup(body); await verifySession(); },
    signOut, retry: () => { void query.refetch(); },
  };
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
