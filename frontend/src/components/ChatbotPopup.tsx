import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useAskChatbot } from '../lib/chatbot'
import { Alert } from './Alert'
import { Button } from './Button'
import { FIELD_CLASS } from './TextField'

const MAX_MESSAGE_LENGTH = 1000

interface Bubble {
  author: 'patient' | 'chatbot'
  text: string
}


export function ChatbotPopup() {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [bubbles, setBubbles] = useState<Bubble[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)
  const ask = useAskChatbot()
  const end = useRef<HTMLDivElement>(null)

  useEffect(() => {
    end.current?.scrollIntoView?.({ block: 'end' })
  }, [bubbles, ask.isPending])

  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false)
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open])

  function send(e: FormEvent) {
    e.preventDefault()
    const message = text.trim()
    if (!message || ask.isPending) return
    setBubbles((b) => [...b, { author: 'patient', text: message }])
    setText('')
    ask.mutate(
      { message, conversation_id: conversationId },
      {
        onSuccess: (reply) => {
          setConversationId(reply.conversation_id)
          setBubbles((b) => [...b, { author: 'chatbot', text: reply.answer }])
        },
      },
    )
  }

  if (!open) {
    return (
      <button
        type="button"
        aria-label="Abrir chat"
        aria-expanded={false}
        onClick={() => setOpen(true)}
        className="fixed bottom-4 right-4 z-40 rounded-full bg-teal-700 px-5 py-3 text-sm font-medium text-white shadow-lg hover:bg-teal-800"
      >
        Consultar al chatbot
      </button>
    )
  }

  return (
    <section
      aria-label="Chatbot"
      className="fixed bottom-4 right-4 z-40 flex h-[32rem] max-h-[calc(100vh-2rem)] w-[calc(100vw-2rem)] max-w-sm flex-col rounded-lg border border-slate-300 bg-white shadow-xl"
    >
      <header className="flex items-center justify-between border-b border-slate-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-teal-800">Chatbot de GenLab</h2>
        <button
          type="button"
          aria-label="Cerrar chat"
          onClick={() => setOpen(false)}
          className="rounded px-2 text-lg leading-none text-slate-600 hover:bg-slate-100"
        >
          ×
        </button>
      </header>

      <p className="border-b border-slate-200 bg-slate-50 px-4 py-2 text-xs text-slate-600">
        Asistente automático. No reemplaza a tu médico/a ni da diagnósticos. No escribas datos
        personales.
      </p>

      <div className="flex-1 space-y-2 overflow-y-auto px-4 py-3" aria-live="polite">
        {bubbles.length === 0 && (
          <p className="text-sm text-slate-500">
            Hacé tu consulta sobre el estudio de exoma o las enfermedades lisosomales.
          </p>
        )}
        {bubbles.map((b, i) => (
          <div key={i} className={b.author === 'patient' ? 'text-right' : 'text-left'}>
            <p
              className={`inline-block max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-2 text-left text-sm ${
                b.author === 'patient' ? 'bg-teal-700 text-white' : 'bg-slate-100 text-slate-900'
              }`}
            >
              {b.text}
            </p>
          </div>
        ))}
        {ask.isPending && <p className="text-sm text-slate-500">Escribiendo…</p>}
        {ask.isError && <Alert kind="error">{ask.error.message}</Alert>}
        <div ref={end} />
      </div>

      <form onSubmit={send} className="flex items-end gap-2 border-t border-slate-200 p-3">
        <div className="flex-1">
          <label htmlFor="chatbot-message" className="sr-only">
            Tu consulta
          </label>
          <input
            id="chatbot-message"
            value={text}
            maxLength={MAX_MESSAGE_LENGTH}
            autoComplete="off"
            placeholder="Escribí tu consulta"
            onChange={(e) => setText(e.target.value)}
            className={FIELD_CLASS}
          />
        </div>
        <Button type="submit" loading={ask.isPending} disabled={!text.trim()}>
          Enviar
        </Button>
      </form>
    </section>
  )
}
