"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ArrowRight, Leaf } from "lucide-react";

import { ApiError } from "@/lib/api";
import { useAuth } from "@/context/auth-context";

export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const isRegister = mode === "register";
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, register } = useAuth();
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError(null);
    const data = new FormData(event.currentTarget);
    try {
      if (isRegister) {
        await register({
          email: String(data.get("email")),
          password: String(data.get("password")),
          first_name: String(data.get("first_name")),
          last_name: String(data.get("last_name")),
        });
        router.replace("/login?registered=1");
      } else {
        await login(String(data.get("email")), String(data.get("password")));
        const next = searchParams.get("next");
        router.replace(next?.startsWith("/") && !next.startsWith("//") ? next : "/dashboard");
      }
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Something went wrong. Please try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-visual" aria-label="EcoTrack">
        <div className="auth-visual-grain" />
        <Link className="brand-lockup auth-brand" href="/">
          <span className="brand-mark"><Leaf size={18} /></span>
          <span className="brand-name">ecotrack<span>.</span></span>
        </Link>
        <div className="auth-visual-copy">
          <span className="eyebrow light-eyebrow">A clearer footprint</span>
          <h1>Know what<br />moves the needle.</h1>
          <p>Track daily choices. Find the changes that matter. Keep your progress in view.</p>
        </div>
        <div className="auth-visual-footer">
          <span>Measure what matters.</span>
          <span className="visual-orbit" aria-hidden="true"><i /><i /><i /></span>
        </div>
      </section>

      <section className="auth-panel">
        <div className="auth-panel-inner">
          <div className="auth-kicker">{isRegister ? "Start tracking" : "Welcome back"}</div>
          <h2>{isRegister ? "Create your account" : "Sign in to EcoTrack"}</h2>
          <p className="auth-intro">
            {isRegister ? "A personal view of your everyday emissions." : "Your activity, progress, and next steps are waiting."}
          </p>
          {searchParams.get("registered") === "1" && !isRegister && (
            <div className="form-success" role="status">Account created. Sign in to continue.</div>
          )}
          <form className="auth-form" onSubmit={handleSubmit}>
            {isRegister && (
              <div className="form-grid-two">
                <label className="field-label">First name
                  <input autoComplete="given-name" name="first_name" required minLength={1} maxLength={100} />
                </label>
                <label className="field-label">Last name
                  <input autoComplete="family-name" name="last_name" required minLength={1} maxLength={100} />
                </label>
              </div>
            )}
            <label className="field-label">Email address
              <input autoComplete="email" name="email" type="email" required maxLength={320} />
            </label>
            <label className="field-label">Password
              <input
                autoComplete={isRegister ? "new-password" : "current-password"}
                name="password"
                type="password"
                required
                minLength={isRegister ? 12 : 1}
                maxLength={128}
              />
              {isRegister && <span className="field-hint">At least 12 characters, with a letter and a number.</span>}
            </label>
            {error && <div className="form-error" role="alert">{error}</div>}
            <button className="button-primary auth-submit" disabled={pending} type="submit">
              <span>{pending ? "Please wait…" : isRegister ? "Create account" : "Sign in"}</span>
              <ArrowRight size={17} />
            </button>
          </form>
          <p className="auth-switch">
            {isRegister ? "Already have an account?" : "New to EcoTrack?"}{" "}
            <Link href={isRegister ? "/login" : "/register"}>{isRegister ? "Sign in" : "Create an account"}</Link>
          </p>
          <p className="auth-legal">By continuing, you agree to use EcoTrack responsibly and keep your account details secure.</p>
        </div>
      </section>
    </main>
  );
}