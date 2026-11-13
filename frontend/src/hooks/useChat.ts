import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, postChat } from "../lib/api";
import type { ChatMessage, UiMessage } from "../types/chat";

function newId(): string {
  return (
    globalThis.crypto?.randomUUID?.() ??
    `${Date.now()}-${Math.random().toString(16).slice(2)}`
  );
}

function formatError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 422) {
      return `Revisá los datos enviados: ${error.message}`;
    }
    if (error.status === 503) {
      return "El agente o la base documental no están disponibles en este momento. Verificá que Ollama esté activo y reintentá.";
    }
    return `La API respondió con un error (${error.status}): ${error.message}`;
  }

  if (error instanceof DOMException && error.name === "AbortError") {
    return "";
  }

  return "No se pudo conectar con la API. Verificá que el backend esté levantado en http://localhost:8000.";
}

interface SendOptions {
  fresh?: boolean;
}

interface UseChatResult {
  messages: UiMessage[];
  isLoading: boolean;
  error: string | null;
  send: (text: string, options?: SendOptions) => Promise<void>;
  reset: () => void;
  dismissError: () => void;
}

export function useChat(): UseChatResult {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const messagesRef = useRef<UiMessage[]>(messages);
  const loadingRef = useRef(false);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  const send = useCallback(async (text: string, options?: SendOptions) => {
    const trimmed = text.trim();
    if (!trimmed || loadingRef.current) {
      return;
    }

    const fresh = options?.fresh === true;

    loadingRef.current = true;
    setIsLoading(true);
    setError(null);

    const history: ChatMessage[] = fresh
      ? []
      : messagesRef.current.map(({ role, content }) => ({ role, content }));

    const userMessage: UiMessage = {
      id: newId(),
      role: "user",
      content: trimmed,
    };
    setMessages((previous) => {
      const next = fresh ? [userMessage] : [...previous, userMessage];
      messagesRef.current = next;
      return next;
    });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const data = await postChat({ message: trimmed, history }, controller.signal);
      setMessages((previous) => {
        const next: UiMessage[] = [
          ...previous,
          {
            id: newId(),
            role: "assistant",
            content: data.respuesta,
            herramientas: data.herramientas_usadas,
            pasos: data.pasos,
          },
        ];
        messagesRef.current = next;
        return next;
      });
    } catch (caught) {
      if (controller.signal.aborted) {
        return;
      }
      setError(formatError(caught));
    } finally {
      if (abortRef.current === controller) {
        abortRef.current = null;
        loadingRef.current = false;
        setIsLoading(false);
      }
    }
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    loadingRef.current = false;
    messagesRef.current = [];
    setMessages([]);
    setError(null);
    setIsLoading(false);
  }, []);

  const dismissError = useCallback(() => setError(null), []);

  return { messages, isLoading, error, send, reset, dismissError };
}
