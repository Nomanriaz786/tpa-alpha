import type { ReactNode } from 'react'
import { AlertCircle, CheckCircle2, Info, TriangleAlert } from 'lucide-react'
import { cn } from '../../lib/utils'

type AlertVariant = 'info' | 'success' | 'warning' | 'destructive'

const variantStyles: Record<AlertVariant, string> = {
  info: 'border-primary/25 bg-primary/10 text-slate-100',
  success: 'border-success/25 bg-success/10 text-slate-100',
  warning: 'border-warning/25 bg-warning/10 text-slate-100',
  destructive: 'border-destructive/25 bg-destructive/10 text-slate-100',
}

const iconMap: Record<AlertVariant, ReactNode> = {
  info: <Info className="size-4" />,
  success: <CheckCircle2 className="size-4" />,
  warning: <TriangleAlert className="size-4" />,
  destructive: <AlertCircle className="size-4" />,
}

export function Alert({
  variant = 'info',
  title,
  children,
  className,
}: {
  variant?: AlertVariant
  title?: string
  children: ReactNode
  className?: string
}) {
  return (
    <div className={cn('rounded-2xl border p-4', variantStyles[variant], className)}>
      <div className="flex items-start gap-3">
        <div className="mt-0.5 text-current">{iconMap[variant]}</div>
        <div className="space-y-1">
          {title ? <p className="text-sm font-semibold">{title}</p> : null}
          <div className="text-sm leading-6 text-slate-300">{children}</div>
        </div>
      </div>
    </div>
  )
}
