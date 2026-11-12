import { useMutation } from '@tanstack/react-query'
import { api, json } from './api'

export type ReplyKind = 'respuesta' | 'fuera_de_alcance' | 'derivar_medico' | 'sin_informacion'

export interface ChatbotReply {
  answer: string
  conversation_id: string
  kind: ReplyKind
}

export interface ChatbotQuestion {
  message: string
  conversation_id: string | null
}

export function useAskChatbot() {
  return useMutation({
    mutationFn: (question: ChatbotQuestion) =>
      api<ChatbotReply>('/chatbot/messages', { method: 'POST', ...json(question) }),
  })
}
