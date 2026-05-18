"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";

const STORAGE_KEY = "parlay-calculator:legs";

export interface ParlayLeg {
  id: string;
  description: string;
  americanOdds: number;
  oppositeOdds?: number;
  gameId: string;
  team: string;
  sportKey: string;
  book: string;
}

interface ParlayContextValue {
  legs: ParlayLeg[];
  addLeg: (leg: ParlayLeg) => void;
  removeLeg: (id: string) => void;
  hasLeg: (id: string) => boolean;
  clear: () => void;
}

const ParlayContext = createContext<ParlayContextValue | null>(null);

export function ParlayProvider({ children }: { children: ReactNode }) {
  const [legs, setLegs] = useState<ParlayLeg[]>([]);
  const [hydrated, setHydrated] = useState(false);

  // Load from localStorage once, after first render
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setLegs(parsed);
        }
      }
    } catch {
      // localStorage unavailable or corrupted; start empty
    }
    setHydrated(true);
  }, []);

  // Save to localStorage whenever legs change, but never on the very first
  // render (otherwise we'd overwrite the stored value with [] before loading)
  useEffect(() => {
    if (!hydrated) return;
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(legs));
    } catch {
      // quota exceeded or storage disabled; silently ignore
    }
  }, [legs, hydrated]);

  const addLeg = (leg: ParlayLeg) => {
    setLegs((prev) =>
      prev.some((l) => l.id === leg.id) ? prev : [...prev, leg],
    );
  };

  const removeLeg = (id: string) => {
    setLegs((prev) => prev.filter((l) => l.id !== id));
  };

  const hasLeg = (id: string) => legs.some((l) => l.id === id);

  const clear = () => setLegs([]);

  return (
    <ParlayContext.Provider
      value={{ legs, addLeg, removeLeg, hasLeg, clear }}
    >
      {children}
    </ParlayContext.Provider>
  );
}

export function useParlay(): ParlayContextValue {
  const ctx = useContext(ParlayContext);
  if (!ctx) {
    throw new Error("useParlay must be used inside a ParlayProvider");
  }
  return ctx;
}
