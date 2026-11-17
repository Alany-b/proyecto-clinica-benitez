export type ViewMode = "chat" | "scenarios";

interface ModeTabsProps {
  mode: ViewMode;
  onChange: (mode: ViewMode) => void;
  scenarioCount: number;
}

interface TabDefinition {
  id: ViewMode;
  label: string;
  hint: string;
  icon: "chat" | "flask";
}

const TABS: TabDefinition[] = [
  {
    id: "chat",
    label: "Conversar con el agente",
    hint: "Consulta libre",
    icon: "chat",
  },
  {
    id: "scenarios",
    label: "Escenarios de prueba",
    hint: "Consultas guiadas",
    icon: "flask",
  },
];

function TabIcon({ icon }: { icon: TabDefinition["icon"] }) {
  if (icon === "flask") {
    return (
      <svg
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.7"
        className="h-4 w-4"
        aria-hidden="true"
      >
        <path
          d="M9 3h6M10 3v5.2a4 4 0 0 1-.6 2.1L5 18a2.4 2.4 0 0 0 2 3.6h10a2.4 2.4 0 0 0 2-3.6l-4.4-7.7a4 4 0 0 1-.6-2.1V3M7 15h10"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }

  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      className="h-4 w-4"
      aria-hidden="true"
    >
      <path
        d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5Z"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function ModeTabs({ mode, onChange, scenarioCount }: ModeTabsProps) {
  return (
    <div className="border-b border-slate-800/80 bg-slate-950/60 px-3 py-2 sm:px-5 lg:px-6">
      <div
        role="tablist"
        aria-label="Modo de uso del asistente"
        className="mx-auto flex w-full max-w-4xl items-center gap-1.5 rounded-xl border border-slate-800/80 bg-slate-900/50 p-1"
      >
        {TABS.map((tab) => {
          const isActive = tab.id === mode;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              aria-controls="panel-principal"
              onClick={() => onChange(tab.id)}
              className={`group flex min-w-0 flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-left transition focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400/60 sm:justify-start ${
                isActive
                  ? "bg-teal-400/10 text-teal-100 shadow-sm shadow-teal-500/10 ring-1 ring-inset ring-teal-400/30"
                  : "text-slate-400 hover:bg-slate-800/60 hover:text-slate-200"
              }`}
            >
              <span
                className={`hidden shrink-0 sm:inline-flex ${
                  isActive ? "text-teal-300" : "text-slate-500"
                }`}
              >
                <TabIcon icon={tab.icon} />
              </span>
              <span className="min-w-0">
                <span className="block truncate text-xs font-semibold sm:text-sm">
                  {tab.label}
                </span>
                <span className="hidden truncate text-[11px] text-slate-500 sm:block">
                  {tab.hint}
                </span>
              </span>
              {tab.id === "scenarios" && (
                <span
                  className={`ml-auto hidden shrink-0 items-center rounded-full px-2 py-0.5 text-[10px] font-bold sm:inline-flex ${
                    isActive
                      ? "bg-teal-400/15 text-teal-200"
                      : "bg-slate-800 text-slate-400"
                  }`}
                >
                  {scenarioCount}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
