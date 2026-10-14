"use client";
import { createContext, useContext } from "react";
import type { Me } from "@/lib/types";

export const AuthContext = createContext<Me | null>(null);
export function useAuth(): Me {
  const me = useContext(AuthContext);
  if (!me) throw new Error("useAuth must be used inside the dashboard layout");
  return me;
}
