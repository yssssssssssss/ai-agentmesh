import { Bot, FileText, UserRound } from 'lucide-react'

import type { ChatMessage, Source } from '../../features/workspace/types'

interface PendingMessage {
  content: string
  status: 'sending' | 'retryable' | 'processing' | 'failed' | 'unknown'
}

const PENDING_STATUS_LABEL: Record<PendingMessage['status'], string> = {
  sending: '正在发送…',
  retryable: '服务端未收到，可安全重试',
  processing: '服务端已受理，正在核对状态',
  failed: '服务端已受理但未完成',
  unknown: '暂时无法核对服务端状态',
}

interface ConversationThreadProps {
  title?: string
  messages: ChatMessage[]
  pending: PendingMessage | null
  loading: boolean
  onOpenSource: (source: Source) => void
}

function Provenance({ message }: { message: ChatMessage }) {
  const trace = message.workflow_trace
  if (!trace) return null
  return (
    <dl data-testid="provider-provenance" className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-slate-500">
      <div className="flex gap-1"><dt>请求提供方</dt><dd className="text-slate-300">{trace.requested_provider ?? 'agentmesh'}</dd></div>
      <div className="flex gap-1"><dt>实际提供方</dt><dd className="text-slate-300">{trace.actual_provider ?? trace.requested_provider ?? 'agentmesh'}</dd></div>
      {trace.requested_model ? <div className="flex gap-1"><dt>请求模型</dt><dd className="text-slate-300">{trace.requested_model}</dd></div> : null}
      {trace.actual_model ? <div className="flex gap-1"><dt>实际模型</dt><dd className="text-slate-300">{trace.actual_model}</dd></div> : null}
      <div className="flex gap-1"><dt>模式</dt><dd className="text-slate-300">{trace.provider_mode ?? (trace.llm_used ? 'real' : 'fallback')}</dd></div>
      {trace.latency_ms != null ? <div className="flex gap-1"><dt>延迟</dt><dd className="text-slate-300">{Math.round(trace.latency_ms)} ms</dd></div> : null}
      {trace.fallback_reason ? <div className="flex gap-1"><dt>降级原因</dt><dd className="text-amber-300">{trace.fallback_reason}</dd></div> : null}
      {trace.model_fallback_reason ? <div className="flex gap-1"><dt>模型切换原因</dt><dd className="text-amber-300">{trace.model_fallback_reason}</dd></div> : null}
      <div className="flex gap-1"><dt>工作流</dt><dd className="text-slate-300">{trace.selected_workflow}</dd></div>
    </dl>
  )
}

export function ConversationThread({ title, messages, pending, loading, onOpenSource }: ConversationThreadProps) {
  return (
    <section aria-label="对话内容" className="space-y-6">
      <header className="border-b border-white/[0.06] pb-4">
        <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-mint-300">AI 工作台</p>
        <h1 className="mt-1.5 text-xl font-semibold text-white">{title ?? 'AI 工作台'}</h1>
      </header>

      {loading ? <p className="py-10 text-center text-sm text-slate-500">正在加载对话…</p> : null}
      {!loading && messages.length === 0 && !pending ? (
        <div className="rounded-[14px] border border-dashed border-white/[0.1] px-5 py-12 text-center">
          <Bot className="mx-auto h-6 w-6 text-mint-300" aria-hidden="true" />
          <p className="mt-3 text-sm text-slate-300">选择一个对话，或发送第一条消息开始。</p>
        </div>
      ) : null}

      {messages.map((message) => (
        <article key={message.id} className={message.role === 'user' ? 'flex justify-end gap-3' : 'flex gap-3'}>
          {message.role === 'assistant' ? (
            <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-mint-400/10 text-mint-300">
              <Bot className="h-4 w-4" aria-hidden="true" />
            </span>
          ) : null}
          <div
            data-testid={message.role === 'assistant' ? 'assistant-message' : 'user-message'}
            className={message.role === 'user'
              ? 'max-w-[85%] rounded-[14px] rounded-tr-sm bg-surface-3 px-4 py-3 text-sm leading-6 text-slate-100'
              : 'min-w-0 max-w-[92%] rounded-[14px] rounded-tl-sm border border-white/[0.06] bg-surface-1 px-4 py-3 text-sm leading-6 text-slate-200'}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
            {message.sources && message.sources.length > 0 ? (
              <div className="mt-3 flex flex-wrap gap-2 border-t border-white/[0.06] pt-3">
                {message.sources.map((source, index) => (
                  <button
                    key={source.id ?? `${source.reference}-${index}`}
                    type="button"
                    aria-label={source.title}
                    onClick={() => onOpenSource(source)}
                    className="flex items-center gap-1.5 rounded-full bg-white/[0.05] px-2.5 py-1 text-xs text-slate-300 hover:bg-white/[0.09]"
                  >
                    <FileText className="h-3 w-3" aria-hidden="true" />
                    {source.title}
                  </button>
                ))}
              </div>
            ) : null}
            {message.role === 'assistant' ? <Provenance message={message} /> : null}
          </div>
          {message.role === 'user' ? (
            <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] bg-white/[0.06] text-slate-300">
              <UserRound className="h-4 w-4" aria-hidden="true" />
            </span>
          ) : null}
        </article>
      ))}

      {pending ? (
        <article className="flex justify-end gap-3">
          <div className="max-w-[85%] rounded-[14px] rounded-tr-sm bg-surface-3 px-4 py-3 text-sm leading-6 text-slate-100 opacity-75">
            <p className="whitespace-pre-wrap">{pending.content}</p>
            <p className={`mt-1 text-[11px] ${pending.status === 'sending' ? 'text-slate-500' : 'text-rose'}`}>
              {PENDING_STATUS_LABEL[pending.status]}
            </p>
          </div>
        </article>
      ) : null}
    </section>
  )
}
