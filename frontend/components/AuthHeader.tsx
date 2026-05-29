"use client";

import Link from "next/link";
import { useAuth } from "@/lib/AuthContext";

export default function AuthHeader() {
  const { user, loading, logout } = useAuth();

  return (
    <header className="w-full border-b border-slate-800 bg-slate-950">
      <div className="max-w-5xl mx-auto flex justify-between items-center px-6 py-2 text-sm">
        <Link href="/" className="font-semibold text-slate-200 hover:text-white">
          Parlay Pros
        </Link>

        <div className="flex items-center gap-3">
          {loading ? (
            <span className="text-slate-600">…</span>
          ) : user ? (
            <>
              <span className="text-slate-400">{user.email}</span>
              <button
                onClick={logout}
                className="text-slate-400 hover:text-slate-200"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link
                href="/login"
                className="text-slate-400 hover:text-slate-200"
              >
                Log in
              </Link>
              <Link
                href="/signup"
                className="bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-1 rounded"
              >
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
