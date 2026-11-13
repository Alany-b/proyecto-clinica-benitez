import type { HealthStatus } from "../hooks/useHealth";
import { StatusIndicator } from "./StatusIndicator";

interface HeaderProps {
  status: HealthStatus;
  lastChecked: Date | null;
  onRefreshHealth: () => Promise<void>;
  onNewChat: () => void;
  canReset: boolean;
  onToggleSidebar: () => void;
}

export function Header({
  status,
  lastChecked,
  onRefreshHealth,
  onNewChat,
  canReset,
  onToggleSidebar,
}: HeaderProps) {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-950/85 backdrop-blur">
      <div className="flex h-16 items-center gap-3 px-3 sm:px-5 lg:px-6">
        <button
          type="button"
          onClick={onToggleSidebar}
          className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-800 text-slate-300 transition hover:border-slate-700 hover:bg-slate-900 lg:hidden"
          aria-label="Abrir escenarios de prueba"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="h-5 w-5"
            aria-hidden="true"
          >
            <path d="M4 6h16M4 12h16M4 18h16" strokeLinecap="round" />
          </svg>
        </button>

        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-teal-400 to-cyan-600 text-sm font-bold text-slate-950 shadow-lg shadow-teal-500/20">
          CB
        </div>

        <div className="min-w-0 flex-1">
          <h1 className="truncate text-sm font-semibold text-slate-100 sm:text-base">
            Clínica Benitez{" "}
            <span className="hidden text-slate-400 md:inline">
              — Asistente Administrativo
            </span>
          </h1>
          <p className="truncate text-[11px] text-slate-500 md:hidden">
            Asistente Administrativo
          </p>
        </div>

        <StatusIndicator
          status={status}
          lastChecked={lastChecked}
          onRefresh={onRefreshHealth}
        />

        <button
          type="button"
          onClick={onNewChat}
          disabled={!canReset}
          className="inline-flex h-10 items-center gap-2 rounded-xl border border-slate-800 px-3 text-sm font-medium text-slate-200 transition hover:border-slate-700 hover:bg-slate-900 disabled:cursor-not-allowed disabled:opacity-40"
          title="Reiniciar la conversación"
        >
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            className="h-4 w-4"
            aria-hidden="true"
          >
            <path
              d="M20 11a8 8 0 1 0-2.34 5.66M20 4v7h-7"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="hidden sm:inline">Nueva conversación</span>
        </button>
      </div>
    </header>
  );
}
