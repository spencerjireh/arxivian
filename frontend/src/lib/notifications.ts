// The one wrapper over sonner: every toast in the app goes through `notify`, so tests mock
// this module and the library can be swapped in one place.
import { toast } from 'sonner'

export const notify = {
  success: (title: string, description?: string) =>
    toast.success(title, description ? { description } : undefined),
  error: (title: string, description?: string) =>
    toast.error(title, description ? { description } : undefined),
  /** A neutral toast with an Undo action (a dismissed paper). */
  undoable: (title: string, onUndo: () => void) =>
    toast(title, { action: { label: 'Undo', onClick: onUndo } }),
}
