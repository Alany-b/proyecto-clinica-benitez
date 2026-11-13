import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { UiMessage } from "../types/chat";

const TOOL_LABELS: Record<string, string> = {
  buscar_protocolo: "RAG",
  consultar_contacto_area: "Contacto",
  derivar_solicitud: "Derivación",
};

function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool;
}

interface MessageBubbleProps {
  message: UiMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const tools = message.herramientas ?? [];
  const hasMetadata = !isUser && (tools.length > 0 || Boolean(message.pasos));

  return (
    <article
      className={`animate-fade-in flex gap-3 ${
        isUser ? "flex-row-reverse" : "flex-row"
      }`}
    >
      <div
        className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-[11px] font-bold ${
          isUser
            ? "bg-slate-800 text-slate-200"
            : "bg-gradient-to-br from-teal-400 to-cyan-600 text-slate-950 shadow-md shadow-teal-500/20"
        }`}
        aria-hidden="true"
      >
        {isUser ? "Tú" : "CB"}
      </div>

      <div className={`min-w-0 max-w-[88%] sm:max-w-[80%] ${isUser ? "text-right" : ""}`}>
        <div
          className={`inline-block rounded-2xl px-4 py-3 text-left shadow-sm ${
            isUser
              ? "rounded-tr-md bg-teal-400 text-slate-950"
              : "rounded-tl-md border border-slate-800 bg-slate-900/70 text-slate-200"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">
              {message.content}
            </p>
          ) : (
            <div className="markdown">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {hasMetadata && (
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            {tools.map((tool) => {
              const isDerivation = tool === "derivar_solicitud";
              return (
                <span
                  key={tool}
                  title={tool}
                  className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                    isDerivation
                      ? "border-amber-400/40 bg-amber-400/10 text-amber-200"
                      : "border-slate-700 bg-slate-800/80 text-slate-300"
                  }`}
                >
                  {isDerivation && (
                    <svg
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      className="h-3 w-3"
                      aria-hidden="true"
                    >
                      <path
                        d="M12 9v4m0 4h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      />
                    </svg>
                  )}
                  {toolLabel(tool)}
                </span>
              );
            })}

            {typeof message.pasos === "number" && message.pasos > 0 && (
              <span className="inline-flex items-center rounded-full border border-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-500">
                {message.pasos} {message.pasos === 1 ? "paso" : "pasos"}
              </span>
            )}
          </div>
        )}
      </div>
    </article>
  );
}
