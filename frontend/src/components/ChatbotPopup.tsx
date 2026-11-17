import { useCallback, useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from 'react'
import { ApiError } from '../lib/api'
import { useAskChatbot, type ReplyKind } from '../lib/chatbot'
import { Button } from './Button'
import { FIELD_CLASS } from './TextField'

const MAX_MESSAGE_LENGTH = 1000
const COUNTER_FROM = 800
const STORAGE_KEY = 'genlab.chatbot'

type Item =
  | { id: number; type: 'patient'; text: string }
  | { id: number; type: 'chatbot'; text: string; kind: ReplyKind }
  | { id: number; type: 'error'; text: string; canRetry: boolean }

interface Saved {
  conversationId: string | null
  items: Item[]
}

/** Kinds that get a subtle label so the patient understands why there is no direct answer. */
const KIND_LABEL: Partial<Record<ReplyKind, string>> = {
  fuera_de_alcance: 'Fuera de alcance',
  derivar_medico: 'Consultá con tu médico/a',
}

function loadSaved(): Saved {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw) as Saved
  } catch {
    // Storage can be blocked: the chat still works, it just does not survive a reload.
  }
  return { conversationId: null, items: [] }
}

function save(state: Saved) {
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  } catch {
    // See loadSaved.
  }
}

/** Plain-language text for each failure of the service; 503 shows the service's own message. */
function errorText(error: unknown): { text: string; retryAfter?: number; canRetry: boolean } {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return { text: 'No pudimos conectarnos con el asistente. Avisá al equipo.', canRetry: false }
    }
    if (error.status === 422) {
      return {
        text: `Tu mensaje no se envió. Escribí una pregunta de hasta ${MAX_MESSAGE_LENGTH} caracteres.`,
        canRetry: false,
      }
    }
    if (error.status === 429) {
      const wait = error.retryAfter
      return {
        text: `Hiciste muchas consultas seguidas. Probá de nuevo en ${wait ? `${wait} segundos` : 'unos segundos'}.`,
        retryAfter: wait ?? 10,
        canRetry: false,
      }
    }
    if (error.status === 503) return { text: error.message, canRetry: false }
  }
  return { text: 'Algo salió mal. Probá de nuevo.', canRetry: true }
}

export function ChatbotPopup() {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const [saved, setSaved] = useState<Saved>(loadSaved)
  const [cooldown, setCooldown] = useState(0)
  const [viewportHeight, setViewportHeight] = useState<number | null>(null)
  const ask = useAskChatbot()

  const panel = useRef<HTMLDivElement>(null)
  const list = useRef<HTMLDivElement>(null)
  const input = useRef<HTMLTextAreaElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const nextId = useRef(saved.items.reduce((max, item) => Math.max(max, item.id), 0) + 1)
  const stickToBottom = useRef(true)
  const wasOpen = useRef(false)
  const lastMessage = useRef('')

  const { items, conversationId } = saved
  const tooLong = text.length > MAX_MESSAGE_LENGTH
  const blocked = ask.isPending || cooldown > 0
  const canSend = text.trim().length > 0 && !tooLong && !blocked

  const update = useCallback((change: (state: Saved) => Saved) => {
    setSaved((state) => {
      const next = change(state)
      save(next)
      return next
    })
  }, [])

  const close = useCallback(() => setOpen(false), [])

  // Focus: into the field when it opens, back to the floating button when it closes.
  useEffect(() => {
    if (open) input.current?.focus()
    else if (wasOpen.current) launcher.current?.focus()
    wasOpen.current = open
  }, [open])

  // On phones the sheet is a modal: lock the page behind it and follow the on-screen keyboard.
  useEffect(() => {
    if (!open) return
    document.body.style.overflow = 'hidden'
    const viewport = window.visualViewport
    const onResize = () => viewport && setViewportHeight(viewport.height)
    onResize()
    viewport?.addEventListener('resize', onResize)
    return () => {
      document.body.style.overflow = ''
      viewport?.removeEventListener('resize', onResize)
    }
  }, [open])

  // Scroll to the newest message, but only if the patient was already at the bottom.
  useEffect(() => {
    const el = list.current
    if (el && stickToBottom.current) el.scrollTop = el.scrollHeight
  }, [items, ask.isPending, open])

  useEffect(() => {
    if (cooldown <= 0) return
    const timer = setTimeout(() => setCooldown((s) => s - 1), 1000)
    return () => clearTimeout(timer)
  }, [cooldown])

  function onScroll() {
    const el = list.current
    if (el) stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 48
  }

  function onPanelKeyDown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      e.stopPropagation()
      close()
      return
    }
    if (e.key !== 'Tab') return
    // Keep Tab inside the dialog while it is open.
    const focusable = panel.current?.querySelectorAll<HTMLElement>(
      'button:not([disabled]), textarea:not([disabled]), [href]',
    )
    if (!focusable?.length) return
    const first = focusable[0]
    const last = focusable[focusable.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  function submit(message: string, appendPatientMessage: boolean) {
    lastMessage.current = message
    stickToBottom.current = true
    update((state) => ({
      ...state,
      items: [
        // A retry replaces the failed attempt instead of stacking messages.
        ...state.items.filter((i) => !(i.type === 'error' && appendPatientMessage === false)),
        ...(appendPatientMessage
          ? [{ id: nextId.current++, type: 'patient' as const, text: message }]
          : []),
      ],
    }))
    ask.mutate(
      { message, conversation_id: conversationId },
      {
        onSuccess: (reply) =>
          update((state) => ({
            conversationId: reply.conversation_id,
            items: [
              ...state.items,
              { id: nextId.current++, type: 'chatbot', text: reply.answer, kind: reply.kind },
            ],
          })),
        onError: (error) => {
          const failure = errorText(error)
          if (failure.retryAfter) setCooldown(failure.retryAfter)
          update((state) => ({
            ...state,
            items: [
              ...state.items,
              {
                id: nextId.current++,
                type: 'error',
                text: failure.text,
                canRetry: failure.canRetry,
              },
            ],
          }))
        },
      },
    )
  }

  function send(e?: FormEvent) {
    e?.preventDefault()
    if (!canSend) return
    submit(text.trim(), true)
    setText('')
  }

  function onFieldKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends, Shift+Enter adds a line break.
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault()
      send()
    }
  }

  function newConversation() {
    ask.reset()
    update(() => ({ conversationId: null, items: [] }))
    input.current?.focus()
  }

  if (!open) {
    return (
      <button
        ref={launcher}
        type="button"
        aria-expanded={false}
        onClick={() => setOpen(true)}
        className="fixed right-[max(1rem,env(safe-area-inset-right))] bottom-[max(1rem,env(safe-area-inset-bottom))] z-30 flex min-h-12 items-center gap-2 rounded-full bg-brand px-5 text-sm font-medium text-white shadow-float transition-colors duration-150 hover:bg-brand-strong"
      >
        <span aria-hidden="true" className="text-lg leading-none">
          💬
        </span>
        <span className="sr-only xs:not-sr-only">Consultar al chatbot</span>
      </button>
    )
  }

  const lastError = items.length > 0 ? items[items.length - 1] : null

  return (
    <div
      ref={panel}
      role="dialog"
      aria-modal="true"
      aria-label="Chatbot"
      onKeyDown={onPanelKeyDown}
      style={viewportHeight ? { height: viewportHeight } : undefined}
      className="animate-sheet-up fixed inset-x-0 bottom-0 z-50 flex h-dvh flex-col bg-surface sm:inset-x-auto sm:right-[max(1rem,env(safe-area-inset-right))] sm:bottom-[max(1rem,env(safe-area-inset-bottom))] sm:h-[35rem] sm:max-h-[calc(100dvh-2rem)] sm:w-[23.75rem] sm:rounded-sheet sm:border sm:border-line-soft sm:shadow-float"
    >
      <header className="flex items-center justify-between gap-2 border-b border-line-soft px-4 py-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:pt-3">
        <h2 className="text-base font-semibold whitespace-nowrap text-brand-strong">
          Chatbot de GenLab
        </h2>
        <div className="flex items-center gap-1">
          {items.length > 0 && (
            <button
              type="button"
              onClick={newConversation}
              className="min-h-11 rounded-control px-2 text-sm font-medium whitespace-nowrap text-brand-strong hover:bg-page"
            >
              Nueva conversación
            </button>
          )}
          <button
            type="button"
            aria-label="Cerrar chat"
            onClick={close}
            className="min-h-11 min-w-11 rounded-control text-2xl leading-none text-muted hover:bg-page"
          >
            ×
          </button>
        </div>
      </header>

      <p className="border-b border-line-soft bg-page px-4 py-2 text-sm text-ink-soft">
        Asistente automático. No reemplaza a tu médico/a ni da diagnósticos. No escribas datos
        personales (nombre, DNI, mail).
      </p>

      <div
        ref={list}
        onScroll={onScroll}
        aria-live="polite"
        className="flex-1 space-y-3 overflow-y-auto overscroll-contain px-4 py-3"
      >
        {items.length === 0 && (
          <p className="text-sm text-muted">
            Hacé tu consulta sobre el estudio de exoma o las enfermedades lisosomales.
          </p>
        )}
        {items.map((item) => {
          if (item.type === 'error') {
            return (
              <div
                key={item.id}
                role="alert"
                className="rounded-control border border-danger-line bg-danger-soft px-3 py-2 text-sm text-danger"
              >
                <p className="break-words">{item.text}</p>
                {item.canRetry && item === lastError && (
                  <button
                    type="button"
                    disabled={ask.isPending}
                    onClick={() => submit(lastMessage.current, false)}
                    className="mt-2 min-h-11 rounded-control border border-danger-line bg-surface px-3 text-sm font-medium text-danger hover:bg-danger-soft"
                  >
                    Reintentar
                  </button>
                )}
              </div>
            )
          }
          const mine = item.type === 'patient'
          return (
            <div key={item.id} className={`flex flex-col ${mine ? 'items-end' : 'items-start'}`}>
              {item.type === 'chatbot' && KIND_LABEL[item.kind] && (
                <span className="mb-1 rounded-full border border-line px-2 py-0.5 text-xs text-muted">
                  {KIND_LABEL[item.kind]}
                </span>
              )}
              <p
                className={`max-w-[85%] whitespace-pre-wrap break-words rounded-card px-3 py-2 text-sm ${
                  mine ? 'bg-brand text-white' : 'border border-line-soft bg-page text-ink'
                }`}
              >
                {item.text}
              </p>
            </div>
          )
        })}
        {ask.isPending && (
          <p className="flex items-center gap-2 text-sm text-muted">
            <span aria-hidden="true" className="flex gap-1">
              <span className="size-1.5 animate-bounce rounded-full bg-muted" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted [animation-delay:150ms]" />
              <span className="size-1.5 animate-bounce rounded-full bg-muted [animation-delay:300ms]" />
            </span>
            Escribiendo…
          </p>
        )}
      </div>

      <form
        onSubmit={send}
        className="border-t border-line-soft p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]"
      >
        <div className="flex items-end gap-2">
          <div className="flex-1">
            <label htmlFor="chatbot-message" className="sr-only">
              Tu consulta
            </label>
            <textarea
              ref={input}
              id="chatbot-message"
              rows={1}
              value={text}
              autoComplete="off"
              placeholder="Escribí tu consulta"
              aria-invalid={tooLong || undefined}
              aria-describedby="chatbot-counter"
              onChange={(e) => setText(e.target.value)}
              onKeyDown={onFieldKeyDown}
              className={`${FIELD_CLASS} mt-0 max-h-32 resize-none`}
            />
          </div>
          <Button type="submit" loading={ask.isPending} disabled={!canSend}>
            Enviar
          </Button>
        </div>
        <p
          id="chatbot-counter"
          className={`mt-1 min-h-5 text-right text-sm ${tooLong ? 'text-danger' : 'text-muted'}`}
        >
          {cooldown > 0
            ? `Podés volver a consultar en ${cooldown} s`
            : text.length >= COUNTER_FROM
              ? `${text.length} / ${MAX_MESSAGE_LENGTH}${tooLong ? ': el mensaje es demasiado largo' : ''}`
              : ''}
        </p>
      </form>
    </div>
  )
}
