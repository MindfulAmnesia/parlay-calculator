"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { API_URL } from "@/lib/api";

const TOKEN_KEY = "parlay-calculator:token";

export interface AuthUser {
  id: number;
  email: string;
  tier: string;
  created_at?: string | null;
}

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(null);
  // `loading` is true until we've checked localStorage and (if a token
  // exists) verified it against the backend. Prevents a flash of
  // "logged out" on every page load.
  const [loading, setLoading] = useState(true);

  // On first mount: read any stored token, then confirm it's still valid
  // by asking the backend who it belongs to.
  useEffect(() => {
    let stored: string | null = null;
    try {
      stored = localStorage.getItem(TOKEN_KEY);
    } catch {
      stored = null;
    }

    if (!stored) {
      setLoading(false);
      return;
    }

    setToken(stored);

    (async () => {
      try {
        const res = await fetch(`${API_URL}/auth/me`, {
          headers: { Authorization: `Bearer ${stored}` },
        });
        if (res.ok) {
          setUser(await res.json());
        } else {
          // Token expired or invalid — clear it.
          clearToken();
          setToken(null);
        }
      } catch {
        // Network error — keep the token, leave user null; they can retry.
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function storeToken(t: string) {
    try {
      localStorage.setItem(TOKEN_KEY, t);
    } catch {
      // storage unavailable; token stays in memory only for this session
    }
  }

  function clearToken() {
    try {
      localStorage.removeItem(TOKEN_KEY);
    } catch {
      // ignore
    }
  }

  async function authenticate(
    path: "/auth/login" | "/auth/signup",
    email: string,
    password: string,
  ) {
    const res = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      let detail = "Authentication failed.";
      try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
      } catch {
        // non-JSON error; keep generic message
      }
      throw new Error(detail);
    }

    const data = await res.json();
    setToken(data.token);
    setUser(data.user);
    storeToken(data.token);
  }

  const login = (email: string, password: string) =>
    authenticate("/auth/login", email, password);

  const signup = (email: string, password: string) =>
    authenticate("/auth/signup", email, password);

  function logout() {
    // Best-effort server-side session delete; clear locally regardless.
    if (token) {
      fetch(`${API_URL}/auth/logout`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      }).catch(() => {
        // ignore network errors on logout
      });
    }
    setUser(null);
    setToken(null);
    clearToken();
  }

  return (
    <AuthContext.Provider
      value={{ user, token, loading, login, signup, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside an AuthProvider");
  }
  return ctx;
}
