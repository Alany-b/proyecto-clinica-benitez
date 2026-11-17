import { useState } from "react";

import { ChatWindow, type ChatEmptyState } from "./components/ChatWindow";
import { Header } from "./components/Header";
import { ModeTabs, type ViewMode } from "./components/ModeTabs";
import { SCENARIOS, Sidebar } from "./components/Sidebar";
import { useChat } from "./hooks/useChat";
import { useHealth } from "./hooks/useHealth";

export default function App() {
  const { status, lastChecked, refresh } = useHealth();
  const chat = useChat();
  const scenarios = useChat();
  const [mode, setMode] = useState<ViewMode>("chat");
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const active = mode === "chat" ? chat : scenarios;

  function handleModeChange(next: ViewMode) {
    setMode(next);
    setSidebarOpen(false);
  }

  function handleScenario(prompt: string) {
    handleModeChange("scenarios");
    void scenarios.send(prompt, { fresh: true });
  }

  function handleNewChat() {
    active.reset();
    setSidebarOpen(false);
  }

  const chatEmptyState: ChatEmptyState = {
    title: "¿En qué puedo ayudarte?",
    description:
      "Consultá horarios, trámites, requisitos y contactos de la clínica. También puedo registrar una derivación cuando el caso lo requiera.",
    chips: ["RAG institucional", "Contactos", "Derivaciones"],
    action: {
      label: "Probar escenarios de prueba",
      onClick: () => handleModeChange("scenarios"),
    },
  };

  const scenariosEmptyState: ChatEmptyState = {
    title: "Elegí un escenario de prueba",
    description:
      "Los escenarios de la izquierda envían la consulta automáticamente y reinician el historial. También podés escribir una consulta propia para probar al agente.",
    chips: ["RAG", "Contacto", "Aclaración", "Emergencia", "Límite documental"],
  };

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-slate-950 text-slate-100">
      <Header
        status={status}
        lastChecked={lastChecked}
        onRefreshHealth={refresh}
        onNewChat={handleNewChat}
        canReset={active.messages.length > 0 || active.isLoading}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
        showSidebarToggle={mode === "scenarios"}
      />

      <ModeTabs
        mode={mode}
        onChange={handleModeChange}
        scenarioCount={SCENARIOS.length}
      />

      {mode === "chat" ? (
        <main className="flex min-h-0 flex-1 flex-col">
          <ChatWindow
            messages={chat.messages}
            isLoading={chat.isLoading}
            error={chat.error}
            onSend={(text) => void chat.send(text)}
            onDismissError={chat.dismissError}
            emptyState={chatEmptyState}
            placeholder="Escribí tu consulta administrativa…"
          />
        </main>
      ) : (
        <div className="flex min-h-0 flex-1 overflow-hidden">
          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onSelect={handleScenario}
            disabled={scenarios.isLoading}
          />

          <main className="flex min-w-0 flex-1 flex-col">
            <ChatWindow
              messages={scenarios.messages}
              isLoading={scenarios.isLoading}
              error={scenarios.error}
              onSend={(text) => void scenarios.send(text)}
              onDismissError={scenarios.dismissError}
              emptyState={scenariosEmptyState}
              placeholder="Escribí una consulta de prueba…"
            />
          </main>
        </div>
      )}
    </div>
  );
}
