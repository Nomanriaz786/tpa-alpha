import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { X } from 'lucide-react'
import { cn } from '../../lib/utils'

interface ModalProps {
  open: boolean
  onClose: () => void
  titleLabel?: string
  title: string
  subtitle?: ReactNode
  children: ReactNode
  footer?: ReactNode
  maxWidthClassName?: string
}

export function Modal({
  open,
  onClose,
  titleLabel,
  title,
  subtitle,
  children,
  footer,
  maxWidthClassName = 'max-w-3xl',
}: ModalProps) {
  useEffect(() => {
    if (!open) {
      return
    }

    const originalOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', handleEscape)

    return () => {
      document.body.style.overflow = originalOverflow
      window.removeEventListener('keydown', handleEscape)
    }
  }, [open, onClose])

  if (!open) {
    return null
  }

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-black/75 p-3 sm:p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          'mx-auto w-full overflow-hidden rounded-[1.75rem] border border-white/10 bg-slate-950 shadow-2xl',
          maxWidthClassName
        )}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4 border-b border-white/10 p-4 sm:p-5">
          <div className="min-w-0">
            {titleLabel ? (
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-400">
                {titleLabel}
              </p>
            ) : null}
            <h3 className="mt-2 truncate text-2xl font-semibold text-white">{title}</h3>
            {subtitle ? <div className="mt-1 text-sm text-slate-300">{subtitle}</div> : null}
          </div>

          <button
            type="button"
            onClick={onClose}
            className="inline-flex size-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-white transition-colors hover:bg-white/10"
            aria-label="Close details"
          >
            <X className="size-5" />
          </button>
        </div>

        <div className="max-h-[calc(100vh-11rem)] overflow-y-auto p-4 sm:p-5">{children}</div>

        {footer ? <div className="border-t border-white/10 p-4 sm:p-5">{footer}</div> : null}
      </div>
    </div>
  )
}