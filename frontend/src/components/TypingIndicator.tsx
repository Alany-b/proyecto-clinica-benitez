export function TypingIndicator() {
  return (
    <div className="animate-fade-in flex gap-3" aria-live="polite">
      <div
        className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-teal-400 to-cyan-600 text-[11px] font-bold text-slate-950 shadow-md shadow-teal-500/20"
        aria-hidden="true"
      >
        CB
      </div>

      <div className="rounded-2xl rounded-tl-md border border-slate-800 bg-slate-900/70 px-4 py-3">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((index) => (
            <span
              key={index}
              className="typing-dot h-1.5 w-1.5 rounded-full bg-teal-300"
              style={{ animationDelay: `${index * 160}ms` }}
            />
          ))}
        </div>
        <p className="mt-2 text-xs text-slate-500">
          Consultando la documentación institucional…
        </p>
      </div>
    </div>
  );
}
