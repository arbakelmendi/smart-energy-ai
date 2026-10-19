import { parseDemoSession } from "./demo-session";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

export type Role = "Building Admin" | "Analyst" | "Viewer" | "Platform Admin";

export type SessionUser = {
  name: string;
  email: string;
  role: Role;
  onboarded: boolean;
};

type AuthCtx = {
  user: SessionUser | null;
  ready: boolean;
  signIn: (email: string, role?: Role) => SessionUser;
  signUp: (name: string, email: string, role: Role) => SessionUser;
  signOut: () => void;
  update: (patch: Partial<SessionUser>) => void;
};

const KEY = "sea-session";

const DEMO: SessionUser = {
  name: "Prototype visitor",
  email: "demo@example.invalid",
  role: "Platform Admin",
  onboarded: true,
};

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx);

function nameFromEmail(email: string) {
  const raw = email.split("@")[0] ?? "user";
  return raw
    .split(/[._-]/)
    .filter(Boolean)
    .map((p) => p[0]!.toUpperCase() + p.slice(1))
    .join(" ");
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(KEY);
      if (raw) setUser(parseDemoSession(raw));
    } catch {
      /* ignore corrupt session */
    }
    setReady(true);
  }, []);

  const persist = useCallback((u: SessionUser | null) => {
    setUser(u);
    if (u) window.localStorage.setItem(KEY, JSON.stringify(u));
    else window.localStorage.removeItem(KEY);
  }, []);

  const signIn = useCallback(
    (email: string, role: Role = "Platform Admin") => {
      const u: SessionUser =
        email.trim().toLowerCase() === DEMO.email
          ? DEMO
          : { name: nameFromEmail(email), email, role, onboarded: true };
      persist(u);
      return u;
    },
    [persist],
  );

  const signUp = useCallback(
    (name: string, email: string, role: Role) => {
      const u: SessionUser = { name: name || nameFromEmail(email), email, role, onboarded: false };
      persist(u);
      return u;
    },
    [persist],
  );

  const signOut = useCallback(() => persist(null), [persist]);

  const update = useCallback(
    (patch: Partial<SessionUser>) => {
      setUser((prev) => {
        if (!prev) return prev;
        const next = { ...prev, ...patch };
        window.localStorage.setItem(KEY, JSON.stringify(next));
        return next;
      });
    },
    [],
  );

  return (
    <Ctx.Provider value={{ user, ready, signIn, signUp, signOut, update }}>{children}</Ctx.Provider>
  );
}

export function useAuth() {
  return useContext(Ctx);
}
