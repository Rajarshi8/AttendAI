"use client";

import { ThemeProvider as NextThemesProvider } from "next-themes";
import { ReactNode } from "react";
import { useEffect } from "react";

import { ensureAppwriteConnection } from "@/lib/appwrite";

interface Props {
  children: ReactNode;
}

export function ThemeProvider({ children }: Props) {
  useEffect(() => {
    ensureAppwriteConnection();
  }, []);

  return (
    <NextThemesProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      {children}
    </NextThemesProvider>
  );
}
