import { ArrowUp, Paperclip, RotateCcw, Sparkles } from 'lucide-react'
import { useRef, useState } from 'react'

import type { Skill } from '../../features/workspace/types'
import { cn } from '../../lib/cn'

interface ComposerProps {
  value: string
  skills: Skill[]
  sending: boolean
  sendState: 'retryable' | 'processing' | 'failed' | 'unknown' | null
  statusMessage: string | null
  onChange: (value: string) => void
  onSend: () => void
  onRetry: () => void
  onUpload: (file: File) => void
}

export function Composer({
  value,
  skills,
  sending,
  sendState,
  statusMessage,
  onChange,
  onSend,
  onRetry,
  onUpload,
}: ComposerProps) {
  const [skillsOpen, setSkillsOpen] = useState(false)
  const fileInput = useRef<HTMLInputElement>(null)
  const locked = sendState !== null && sendState !== 'retryable'
  const canRetry = sendState === 'retryable' || sendState === 'processing'

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 bg-gradient-to-t from-base via-base/95 to-transparent px-4 pb-5 pt-10 md:px-6">
      <div className="pointer-events-auto mx-auto max-w-[840px]">
        {sendState ? (
          <div className="mb-2 flex items-center justify-between gap-3 rounded-[10px] border border-rose/25 bg-rose/10 px-3 py-2 text-xs text-rose">
            <span>{statusMessage ?? '发送状态已变化，草稿已保留。'}</span>
            {canRetry ? (
              <button type="button" onClick={onRetry} className="flex shrink-0 items-center gap-1 font-semibold">
                <RotateCcw className="h-3.5 w-3.5" aria-hidden="true" />
                {sendState === 'processing' ? '重新核对' : '重试发送'}
              </button>
            ) : null}
          </div>
        ) : null}
        <div className="relative rounded-[16px] border border-white/[0.08] bg-surface-1 shadow-card focus-within:border-white/[0.16]">
          {skillsOpen ? (
            <div className="absolute bottom-full left-0 mb-2 max-h-72 w-full overflow-y-auto rounded-[12px] border border-white/[0.1] bg-surface-2 p-2 shadow-card sm:w-[420px]">
              {skills.map((skill) => (
                <button
                  key={skill.command}
                  type="button"
                  onClick={() => {
                    onChange(`${skill.command}${skill.requires_input ? ' ' : ''}`)
                    setSkillsOpen(false)
                  }}
                  className="block w-full rounded-[9px] px-3 py-2 text-left hover:bg-white/[0.06]"
                >
                  <span className="block text-xs font-semibold text-mint-300">{skill.command}</span>
                  <span className="mt-0.5 block text-xs text-slate-400">{skill.title} · {skill.description}</span>
                </button>
              ))}
              {skills.length === 0 ? <p className="px-3 py-2 text-xs text-slate-500">暂无可用 Skill</p> : null}
            </div>
          ) : null}
          <textarea
            aria-label="消息"
            value={value}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                onSend()
              }
            }}
            rows={2}
            disabled={sending || locked}
            placeholder="输入问题，或选择 Skill 执行明确工作流…"
            className="max-h-40 w-full resize-none bg-transparent px-4 pt-3.5 text-sm leading-relaxed text-slate-100 placeholder:text-slate-600 focus:outline-none disabled:opacity-60"
          />
          <div className="flex items-center justify-between px-3 pb-3 pt-1">
            <div className="flex items-center gap-1">
              <input
                ref={fileInput}
                type="file"
                aria-label="上传文档"
                className="sr-only"
                onChange={(event) => {
                  const file = event.target.files?.[0]
                  if (file) onUpload(file)
                  event.target.value = ''
                }}
              />
              <button
                type="button"
                onClick={() => fileInput.current?.click()}
                className="flex items-center gap-1.5 rounded-[8px] px-2.5 py-1.5 text-xs text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
              >
                <Paperclip className="h-3.5 w-3.5" aria-hidden="true" />
                上传文档
              </button>
              <button
                type="button"
                aria-expanded={skillsOpen}
                onClick={() => setSkillsOpen((open) => !open)}
                className="flex items-center gap-1.5 rounded-[8px] px-2.5 py-1.5 text-xs text-slate-400 hover:bg-white/[0.05] hover:text-slate-200"
              >
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                选择 Skill
              </button>
            </div>
            <button
              type="button"
              onClick={onSend}
              disabled={!value.trim() || sending || locked}
              className={cn(
                'flex h-8 min-w-8 items-center justify-center rounded-[10px] px-2 transition-all',
                value.trim() && !sending && !locked
                  ? 'bg-mint-400 text-[#06231c] hover:bg-mint-300'
                  : 'cursor-not-allowed bg-white/[0.06] text-slate-600',
              )}
              aria-label="发送"
            >
              {sending ? <span className="text-xs">发送中</span> : <ArrowUp className="h-4 w-4" aria-hidden="true" />}
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-[11px] text-slate-600">回答与来源均来自当前账号可见的服务端数据</p>
      </div>
    </div>
  )
}
