import { AlertCircle } from 'lucide-react'
import { Button } from './Button'
import { Modal } from './Modal'

interface ConfirmationDialogProps {
  open: boolean
  title: string
  message: string
  confirmText?: string
  cancelText?: string
  isDangerous?: boolean
  isLoading?: boolean
  onConfirm: () => void | Promise<void>
  onCancel: () => void
}

export function ConfirmationDialog({
  open,
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDangerous = false,
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmationDialogProps) {
  const handleConfirm = async () => {
    await onConfirm()
  }

  return (
    <Modal
      open={open}
      onClose={onCancel}
      title={title}
      maxWidthClassName="max-w-sm"
      footer={
        <div className="flex w-full flex-wrap items-center justify-end gap-3">
          <Button
            type="button"
            variant="outline"
            className="border-white/10 bg-white/6 text-white hover:bg-white/10"
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelText}
          </Button>
          <Button
            type="button"
            isLoading={isLoading}
            className={
              isDangerous
                ? 'bg-destructive text-white hover:bg-destructive/90'
                : 'bg-accent text-accent-foreground hover:bg-accent/90'
            }
            onClick={handleConfirm}
          >
            {confirmText}
          </Button>
        </div>
      }
    >
      <div className="space-y-4">
        {isDangerous && (
          <div className="flex gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-3">
            <AlertCircle className="mt-0.5 size-5 flex-shrink-0 text-destructive" />
            <p className="text-sm text-destructive">This action cannot be undone.</p>
          </div>
        )}
        <p className="text-sm text-foreground">{message}</p>
      </div>
    </Modal>
  )
}
