import { useState } from "react";

import { ChatWindow } from "./components/ChatWindow";
import { Header } from "./components/Header";
import { Sidebar } from "./components/Sidebar";
import { useChat } from "./hooks/useChat";
import { useHealth } from "./hooks/useHealth";

export default function App() {
  const { status, lastChecked, refresh } = useHealth();
  const { messages, isLoading, error, send, reset, dismissError } = useChat();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  function handleScenario(prompt: string) {
    setSidebarOpen(false);
    void send(prompt, { fresh: true });
  }

  function handleNewChat() {
    reset();
    setSidebarOpen(false);
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-slate-950 text-slate-100">
      <Header
        status={status}
        lastChecked={lastChecked}
        onRefreshHealth={refresh}
        onNewChat={handleNewChat}
        canReset={messages.length > 0 || isLoading}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
      />

      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          onSelect={handleScenario}
          disabled={isLoading}
        />

        <main className="flex min-w-0 flex-1 flex-col">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            error={error}
            onSend={(text) => void send(text)}
            onDismissError={dismissError}
          />
        </main>
      </div>
    </div>
  );
}
