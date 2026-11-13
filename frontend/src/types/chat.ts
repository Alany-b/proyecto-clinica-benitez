export type Role = "user" | "assistant";

export interface ChatMessage {
  role: Role;
  content: string;
}

export interface ChatRequest {
  message: string;
  history: ChatMessage[];
}

export interface ChatResponse {
  respuesta: string;
  herramientas_usadas: string[];
  pasos: number;
}

export interface UiMessage extends ChatMessage {
  id: string;
  herramientas?: string[];
  pasos?: number;
}
