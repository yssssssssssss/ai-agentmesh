import { useRef, useState } from 'react'
import { Paperclip, Sparkles, UserPlus, ArrowUp, Square } from 'lucide-react'
import { useDemo } from '../../store/DemoContext'
import { cn } from '../../lib/cn'

export function Composer() {
  const { showToast } = useDemo()
  const [value, setValue] = useState('')
  const [generating, setGenerating] = useState(false)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  function handleSend() {
    const text = value.trim()
    if (!text || generating) return
    setValue('')
    setGenerating(true)
    showToast('数字人正在补充分析……', 'info')
    timer.current = setTimeout(() => {
      setGenerating(false)
      showToast('数字人已补充回答', 'success')
    }, 1400)
  }

  function handleStop() {
    if (timer.current) clearTimeout(timer.current)
    setGenerating(false)
    showToast('已停止生成', 'info')
  }

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-0 z-10 bg-gradient-to-t from-base via-base/95 to-transparent px-6 pb-5 pt-8">
      <div className="pointer-events-auto mx-auto max-w-[800px]">
        <div className="rounded-[16px] border border-white/[0.08] bg-surface-1 shadow-card transition-colors focus-within:border-white/[0.16]">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            rows={1}
            placeholder="继续询问，或让数字人补充方案、数据与项目经验……"
            className="max-h-40 w-full resize-none bg-transparent px-4 pt-3.5 text-[14px] leading-relaxed text-slate-100 placeholder:text-slate-600 focus:outline-none"
          />
          <div className="flex items-center justify-between px-3 pb-3 pt-1">
            <div className="flex items-center gap-1">
              <ToolButton
                icon={Paperclip}
                label="上传附件"
                onClick={() => showToast('已打开附件上传（演示）', 'info')}
              />
              <ToolButton
                icon={Sparkles}
                label="选择 Skill"
                onClick={() => showToast('已打开 Skill 选择（演示）', 'info')}
              />
              <ToolButton
                icon={UserPlus}
                label="邀请数字分身"
                onClick={() => showToast('已打开数字分身邀请（演示）', 'info')}
              />
            </div>
            {generating ? (
              <button
                onClick={handleStop}
                className="flex items-center gap-1.5 rounded-[10px] border border-white/[0.1] bg-surface-2 px-3 py-2 text-[13px] font-medium text-slate-200 transition-colors hover:bg-surface-3"
              >
                <Square className="h-3 w-3 fill-current" />
                停止生成
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!value.trim()}
                className={cn(
                  'flex h-8 w-8 items-center justify-center rounded-[10px] transition-all',
                  value.trim()
                    ? 'bg-mint-400 text-[#06231c] hover:bg-mint-300 active:scale-95'
                    : 'cursor-not-allowed bg-white/[0.06] text-slate-600',
                )}
                aria-label="发送"
              >
                <ArrowUp className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
        <div className="mt-2 text-center text-[11px] text-slate-600">
          数字人回答基于团队知识与历史项目，请结合实际判断使用
        </div>
      </div>
    </div>
  )
}

function ToolButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof Paperclip
  label: string
  onClick: () => void
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-1.5 rounded-[8px] px-2.5 py-1.5 text-[12px] text-slate-400 transition-colors hover:bg-white/[0.05] hover:text-slate-200"
    >
      <Icon className="h-3.5 w-3.5" />
      <span className="hidden sm:inline">{label}</span>
    </button>
  )
}
