import type { HealthStatus } from "../hooks/useHealth";

const STATUS_META: Record<
  HealthStatus,
  { label: string; dot: string; text: string; border: string }
> = {
  checking: {
    label: "Verificando",
    dot: "bg-amber-400",
    text: "text-amber-200",
    border: "border-amber-400/30 bg-amber-400/5",
  },
  online: {
    label: "Online",
    dot: "bg-emerald-400",
    text: "text-emerald-200",
    border: "border-emerald-400/30 bg-emerald-400/5",
  },
  offline: {
    label: "Error 503",
    dot: "bg-rose-500",
    text: "text-rose-200",
    border: "border-rose-500/30 bg-rose-500/5",
  },
};

interface StatusIndicatorProps {
  status: HealthStatus;
  lastChecked: Date | null;
  onRefresh: () => Promise<void>;
}

export function StatusIndicator({
  status,
  lastChecked,
  onRefresh,
}: StatusIndicatorProps) {
  const meta = STATUS_META[status];
  const checkedAt = lastChecked
    ? lastChecked.toLocaleTimeString("es-AR", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <button
      type="button"
      onClick={() => void onRefresh()}
      title={
        checkedAt
          ? `Última verificación: ${checkedAt}. Clic para verificar ahora.`
          : "Verificar conexión con la API"
      }
      aria-label="Estado de la API. Clic para verificar."
      className={`inline-flex shrink-0 items-center gap-2 rounded-full border px-3 py-1.5 transition hover:brightness-125 focus:outline-none focus-visible:ring-2 focus-visible:ring-teal-400/60 ${meta.border}`}
    >
      <span
        className={`h-2 w-2 rounded-full ${meta.dot} ${
          status === "checking" ? "animate-pulse" : ""
        }`}
      />
      <span className={`text-xs font-semibold ${meta.text}`}>{meta.label}</span>
    </button>
  );
}
