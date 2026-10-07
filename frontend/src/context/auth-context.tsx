"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

import { api, setAccessToken, type User } from "@/lib/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (payload: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }) => Promise<User>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const onUnauthorized = () => {
      setAccessToken(null);
      setUser(null);
      setLoading(false);
    };
    window.addEventListener("ecotrack:unauthorized", onUnauthorized);
    api
      .refresh()
      .then((session) => {
        if (!mounted) return;
        setAccessToken(session.access_token);
        setUser(session.user);
      })
      .catch(() => {
        if (mounted) {
          setAccessToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
      window.removeEventListener("ecotrack:unauthorized", onUnauthorized);
    };
  }, []);

  async function login(email: string, password: string) {
    const session = await api.login({ email, password });
    setAccessToken(session.access_token);
    setUser(session.user);
  }

  async function register(payload: {
    email: string;
    password: string;
    first_name: string;
    last_name: string;
  }) {
    return api.register(payload);
  }

  async function logout() {
    try {
      await api.logout();
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}