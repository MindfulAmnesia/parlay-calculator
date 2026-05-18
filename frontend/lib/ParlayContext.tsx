"use client";

import { createContext, useContext, useState, ReactNode } from "react";

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

  const addLeg = (leg: ParlayLeg) => {
    setLegs((prev) => (prev.some((l) => l.id === leg.id) ? prev : [...prev, leg]));
  };

  const removeLeg = (id: string) => {
    setLegs((prev) => prev.filter((l) => l.id !== id));
  };

  const hasLeg = (id: string) => legs.some((l) => l.id === id);

  const clear = () => setLegs([]);

  return (
    <ParlayContext.Provider value={{ legs, addLeg, removeLeg, hasLeg, clear }}>
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
