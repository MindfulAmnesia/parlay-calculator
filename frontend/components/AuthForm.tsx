"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";

interface AuthFormProps {
  mode: "login" | "signup";
}

export default function AuthForm({ mode }: AuthFormProps) {
  const router = useRouter();
  const { login, signup } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const isSignup = mode === "signup";
  const title = isSignup ? "Create account" : "Log in";
  const cta = isSignup ? "Sign up" : "Log in";

  async function handleSubmit() {
    setError(null);

    if (!email || !password) {
      setError("Email and password are required.");
      return;
    }
    if (isSignup && password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setSubmitting(true);
    try {
      if (isSignup) {
        await signup(email, password);
      } else {
        await login(email, password);
      }
      router.push("/"); // land on the homepage after auth
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-slate-900 text-slate-100 flex items-center justify-center p-8">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold mb-6">{title}</h1>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-slate-400 mb-1">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-slate-100 focus:border-slate-500 focus:outline-none"
              autoComplete="email"
            />
          </div>

          <div>
            <label className="block text-sm text-slate-400 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              className="w-full bg-slate-800 border border-slate-700 rounded p-2 text-slate-100 focus:border-slate-500 focus:outline-none"
              autoComplete={isSignup ? "new-password" : "current-password"}
            />
            {isSignup && (
              <p className="text-xs text-slate-500 mt-1">
                At least 8 characters.
              </p>
            )}
          </div>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            onClick={handleSubmit}
            disabled={submitting}
            className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-600 disabled:cursor-not-allowed text-white py-2 rounded font-medium transition"
          >
            {submitting ? "…" : cta}
          </button>
        </div>

        <p className="text-sm text-slate-400 mt-6 text-center">
          {isSignup ? (
            <>
              Already have an account?{" "}
              <Link href="/login" className="text-emerald-400 hover:text-emerald-300">
                Log in
              </Link>
            </>
          ) : (
            <>
              No account?{" "}
              <Link href="/signup" className="text-emerald-400 hover:text-emerald-300">
                Sign up
              </Link>
            </>
          )}
        </p>
      </div>
    </main>
  );
}
