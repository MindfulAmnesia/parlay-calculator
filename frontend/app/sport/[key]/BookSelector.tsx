"use client";

import { usePathname, useRouter, useSearchParams } from "next/navigation";

const BOOKS: { value: string; label: string }[] = [
  { value: "",              label: "Consensus (median across books)" },
  { value: "draftkings",    label: "DraftKings" },
  { value: "fanduel",       label: "FanDuel" },
  { value: "betmgm",        label: "BetMGM" },
  { value: "caesars",       label: "Caesars" },
  { value: "bovada",        label: "Bovada" },
  { value: "betrivers",     label: "BetRivers" },
  { value: "lowvig",        label: "LowVig.ag" },
  { value: "betonlineag",   label: "BetOnline.ag" },
];

export default function BookSelector({ currentBook }: { currentBook?: string }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newBook = e.target.value;
    const params = new URLSearchParams(searchParams.toString());
    if (newBook) {
      params.set("book", newBook);
    } else {
      params.delete("book");
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