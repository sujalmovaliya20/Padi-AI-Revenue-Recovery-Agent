"use client";

import React from "react";
import { useTheme } from "./ThemeProvider";
import { Sun, Moon } from "lucide-react";

export function ThemeToggle({ className = "" }: { className?: string }) {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      onClick={toggleTheme}
      type="button"
      aria-label={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      title={`Switch to ${theme === "light" ? "dark" : "light"} mode`}
      className={`relative inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-[var(--border-default)] bg-[var(--bg-surface)] text-[var(--text-primary)] hover:border-[var(--brand-accent)] hover:text-[var(--brand-accent)] shadow-card transition-all duration-150 active:scale-95 focus:outline-none focus:ring-2 focus:ring-[var(--border-focus)] ${className}`}
    >
      {theme === "light" ? (
        <Moon className="h-4.5 w-4.5 text-[var(--text-primary)] transition-transform duration-200 hover:rotate-12" />
      ) : (
        <Sun className="h-4.5 w-4.5 text-amber-400 transition-transform duration-200 hover:rotate-45" />
      )}
      <span className="sr-only">Toggle theme</span>
    </button>
  );
}
