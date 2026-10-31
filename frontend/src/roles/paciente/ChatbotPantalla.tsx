
import { useEffect, useRef, useState, type FormEvent } from 'react'

type ChatMessage = {
  id: number
  sender: 'patient' | 'chatbot'
  text: string
}

type ChatResponse = {
  respuesta: string
  conversacion_id: string
  tipo: string
}

type ChatError = {
  detail?: unknown
}

const CHATBOT_API_URL = (
  import.meta.env.VITE_CHATBOT_API_URL ?? 'http://127.0.0.1:8001'
).replace(/\/+$/, '')

const MAX_MESSAGE_LENGTH = 1000

const INITIAL_MESSAGES: ChatMessage[] = [
  {
    id: 1,
    sender: 'chatbot',
    text:
      'Hola. Soy el asistente de GenLab. Podés consultarme sobre ' +
      'estudios genéticos y patologías lisosomales. ' +
      'No realizo diagnósticos ni interpreto resultados personales.',
  },
]

function getErrorMessage(status: number, detail?: unknown): string {
  if (status === 401) {
    return 'No fue posible autorizar la consulta al chatbot.'
  }

  if (status === 429) {
    return 'Realizaste demasiadas consultas. Intentá nuevamente en unos segundos.'
  }

  if (status === 503) {
    return 'El chatbot no está disponible en este momento. Intentá más tarde.'
  }

  if (status === 422) {
    return 'La consulta no es válida. Revisá el texto e intentá nuevamente.'
  }

  if (typeof detail === 'string' && detail.trim()) {
    return detail
  }

  return 'No fue posible obtener una respuesta del chatbot.'
}

export default function ChatbotPantalla() {
  const [messages, setMessages] = useState<ChatMessage[]>(INITIAL_MESSAGES)
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  const conversationId = useRef<string | null>(null)
  const nextId = useRef(2)
  const conversationEnd = useRef<HTMLDivElement | null>(null)
  const requestController = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => {
      requestController.current?.abort()
    }
  }, [])

  useEffect(() => {
    conversationEnd.current?.scrollIntoView({
      behavior: 'smooth',
      block: 'end',
    })
  }, [messages, sending, error])

  function appendMessage(sender: ChatMessage['sender'], text: string) {
    const id = nextId.current++

    setMessages((previous) => [
      ...previous,
      { id, sender, text },
    ])
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    const question = input.trim()

    if (!question || sending) {
      return
    }

    if (question.length > MAX_MESSAGE_LENGTH) {
      setError('La consulta no puede superar los 1000 caracteres.')
      return
    }

    setError('')
    setSending(true)
    setInput('')

    appendMessage('patient', question)

    const controller = new AbortController()
    requestController.current = controller

    try {
      const response = await fetch(`${CHATBOT_API_URL}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mensaje: question,
          conversacion_id: conversationId.current,
        }),
        signal: controller.signal,
      })

      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as ChatError

        throw new Error(getErrorMessage(response.status, body.detail))
      }

      const data = (await response.json()) as ChatResponse

      if (
        typeof data.respuesta !== 'string' ||
        typeof data.conversacion_id !== 'string'
      ) {
        throw new Error('El chatbot devolvió una respuesta inválida.')
      }

      conversationId.current = data.conversacion_id

      appendMessage('chatbot', data.respuesta)
    } catch (caught) {
      if (controller.signal.aborted) {
        return
      }

      setError(
        caught instanceof TypeError
          ? 'No se pudo conectar con el chatbot. Verificá que el servicio esté funcionando.'
          : caught instanceof Error
            ? caught.message
            : 'No fue posible obtener una respuesta del chatbot.',
      )
    } finally {
      if (!controller.signal.aborted) {
        setSending(false)
      }

      if (requestController.current === controller) {
        requestController.current = null
      }
    }
  }

  function handleNewConversation() {
    if (sending) {
      return
    }

    conversationId.current = null
    nextId.current = 2
    setMessages(INITIAL_MESSAGES)
    setInput('')
    setError('')
  }

  return (
    <section className="mx-auto flex max-w-4xl flex-col gap-5 p-2 sm:p-4">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">
          Consultar al chatbot
        </h1>

        <p className="mt-2 text-sm text-slate-600">
          Realizá consultas generales sobre estudios genéticos y
          patologías lisosomales.
        </p>
      </header>

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between gap-3 border-b border-slate-200 bg-teal-50 px-5 py-4">
          <div>
            <h2 className="font-semibold text-teal-900">
              Asistente GenLab
            </h2>

            <p className="mt-1 text-xs text-teal-800">
              Consultas sobre estudios genéticos y patologías lisosomales
            </p>
          </div>

          <button
            type="button"
            onClick={handleNewConversation}
            disabled={sending}
            className="rounded-lg border border-teal-300 px-3 py-2 text-xs font-medium text-teal-900 hover:bg-teal-100 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Nueva conversación
          </button>
        </div>

        <div
          role="log"
          aria-label="Conversación con el chatbot"
          aria-live="polite"
          className="flex h-[420px] flex-col gap-4 overflow-y-auto bg-slate-50 p-4 sm:p-5"
        >
          {messages.map((message) => {
            const fromPatient = message.sender === 'patient'

            return (
              <div
                key={message.id}
                className={`flex ${
                  fromPatient ? 'justify-end' : 'justify-start'
                }`}
              >
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                    fromPatient
                      ? 'rounded-br-md bg-teal-700 text-white'
                      : 'rounded-bl-md border border-slate-200 bg-white text-slate-800'
                  }`}
                >
                  <p className="mb-1 text-xs font-semibold opacity-80">
                    {fromPatient ? 'Vos' : 'Asistente GenLab'}
                  </p>

                  <p className="whitespace-pre-wrap break-words">
                    {message.text}
                  </p>
                </div>
              </div>
            )
          })}

          {sending && (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
                El asistente está respondiendo...
              </div>
            </div>
          )}

          <div ref={conversationEnd} />
        </div>

        <div className="border-t border-slate-200 bg-white p-4">
          {error && (
            <p
              role="alert"
              className="mb-3 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
            >
              {error}
            </p>
          )}

          <form onSubmit={(event) => void handleSubmit(event)}>
            <label
              htmlFor="chatbot-question"
              className="mb-2 block text-sm font-medium text-slate-700"
            >
              Escribí tu consulta
            </label>

            <div className="flex items-end gap-3">
              <textarea
                id="chatbot-question"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                placeholder="Por ejemplo: ¿Qué es la enfermedad de Pompe?"
                rows={2}
                maxLength={MAX_MESSAGE_LENGTH}
                disabled={sending}
                className="min-h-16 flex-1 resize-none rounded-lg border border-slate-300 p-3 text-sm outline-none focus:border-teal-600 disabled:bg-slate-100"
              />

              <button
                type="submit"
                disabled={sending || !input.trim()}
                className="rounded-lg bg-teal-700 px-5 py-3 text-sm font-medium text-white hover:bg-teal-800 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Enviar
              </button>
            </div>

            <p className="mt-2 text-xs text-slate-500">
              Máximo 1000 caracteres. No incluyas información personal
              ni datos de tus estudios.
            </p>
          </form>
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Las respuestas del chatbot son informativas y no reemplazan
        la evaluación de un profesional de salud.
      </p>
    </section>
  )
}
