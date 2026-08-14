import { cn } from '../../lib/cn'

interface DigitalHumanMarkProps {
  size?: number
  online?: boolean
  className?: string
}

/**
 * 数字人抽象身份标识：同心环 + 核心光点，克制的轻微未来感，
 * 避免赛博朋克强发光。
 */
export function DigitalHumanMark({ size = 56, online = true, className }: DigitalHumanMarkProps) {
  return (
    <div
      className={cn('relative shrink-0', className)}
      style={{ width: size, height: size }}
      aria-hidden
    >
      <div className="absolute inset-0 rounded-full bg-gradient-to-br from-mint-400/20 to-knowledge/10 ring-1 ring-inset ring-mint-400/25" />
      <div className="absolute inset-[6px] rounded-full border border-mint-300/30" />
      <div className="absolute inset-[13px] rounded-full border border-mint-200/25" />
      <div className="absolute left-1/2 top-1/2 h-2/5 w-2/5 -translate-x-1/2 -translate-y-1/2 rounded-full bg-mint-300/80 shadow-[0_0_16px_rgba(45,212,168,0.5)]" />
      {online && (
        <span className="absolute -bottom-0.5 -right-0.5 flex h-3.5 w-3.5 items-center justify-center rounded-full bg-surface-1">
          <span className="h-2.5 w-2.5 rounded-full bg-mint-400 ring-2 ring-surface-1" />
        </span>
      )}
    </div>
  )
}
