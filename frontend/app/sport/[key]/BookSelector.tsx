"use client";

import { useEffect } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const STORAGE_KEY = "parlay-calculator:book";

const BOOKS: { value: string; label: string }[] = [
  { value: "",              label: "Consensus (median across books)" },
  { value: "draftkings",    label: "DraftKings" },
  { value: "fanduel",       label: "FanDuel" },
  { value: "betmgm",        label: "BetMGM" },
  { value: "betrivers",     label: "BetRivers" },
  { value: "bovada",        label: "Bovada" },
  { value: "betonlineag",   label: "BetOnline.ag" },
  { value: "betus",         label: "BetUS" },
  { value: "lowvig",        label: "LowVig.ag" },
  { value: "mybookieag",    label: "MyBookie.ag" },
];

export default function BookSelector({ currentBook }: { currentBook?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // On mount: if the URL has no ?book= but we have a saved choice, restore it
  // by redirecting to the same page with the stored book applied.
  useEffect(() => {
    const urlBook = searchParams.get("book");
    if (urlBook) {
      // URL already specifies a book — treat that as the source of truth and
      // remember it for next time.
      try {
        localStorage.setItem(STORAGE_KEY, urlBook);
      } catch {
        // storage unavailable; ignore
      }
      return;
    }
    // No book in the URL — see if we saved one previously.
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved) {
        const params = new URLSearchParams(searchParams.toString());
        params.set("book", saved);
        router.replace(`${pathname}?${params.toString()}`);
      }
    } catch {
      // storage unavailable; stay on consensus
    }
    // We only want this to run on mount / when the path changes, not on every
    // searchParams tick, so dependencies are intentionally limited.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pathname]);

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newBook = e.target.value;
    const params = new URLSearchParams(searchParams.toString());
    if (newBook) {
      params.set("book", newBook);
    } else {
      params.delete("book");
    }
    // Persist the explicit choice (including clearing back to consensus).
    try {
      if (newBook) {
        localStorage.setItem(STORAGE_KEY, newBook);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      // storage unavailable; ignore
    }
    const qs = params.toString();
    router.push(qs ? `${pathname}?${qs}` : pathname);
  }

  return (
    <div className="mb-6">
      <label className="block text-sm text-slate-400 mb-2">
        Bookmaker
      </label>
      <select
        value={currentBook ?? ""}
        onChange={handleChange}
        className="bg-slate-800 text-slate-100 rounded-lg p-2 border border-slate-700 focus:border-slate-500 focus:outline-none"
      >
        {BOOKS.map((b) => (
          <option key={b.value} value={b.value}>
            {b.label}
          </option>
        ))}
      </select>
    </div>
  );
}
