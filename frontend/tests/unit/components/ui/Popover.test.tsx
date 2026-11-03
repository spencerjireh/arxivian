import { render, screen, fireEvent } from '@testing-library/react'
import Popover from '@/components/ui/Popover'

function mount(
  children: React.ComponentProps<typeof Popover>['children'] = <input aria-label="A" />
) {
  render(
    <div>
      <Popover trigger="Filters" label="Filters">
        {children}
      </Popover>
      <button type="button">Elsewhere</button>
    </div>
  )
  return screen.getByRole('button', { name: 'Filters' })
}

describe('Popover', () => {
  it('opens a labelled dialog from the trigger and moves focus inside', () => {
    const trigger = mount()
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    expect(trigger).toHaveAttribute('aria-haspopup', 'dialog')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()

    fireEvent.click(trigger)
    const dialog = screen.getByRole('dialog', { name: 'Filters' })
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
    expect(trigger).toHaveAttribute('aria-controls', dialog.id)
    expect(screen.getByLabelText('A')).toHaveFocus()
  })

  it('focuses the panel itself when nothing inside is focusable', () => {
    const trigger = mount(<p>Nothing here</p>)
    fireEvent.click(trigger)
    expect(screen.getByRole('dialog')).toHaveFocus()
  })

  it('closes on Escape and returns focus to the trigger', () => {
    const trigger = mount()
    fireEvent.click(trigger)
    fireEvent.keyDown(document, { key: 'Escape' })
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
    expect(trigger).not.toHaveAttribute('aria-controls')
  })

  it('closes on a pointerdown outside and stays open on one inside', () => {
    const trigger = mount()
    fireEvent.click(trigger)
    fireEvent.pointerDown(screen.getByLabelText('A'))
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    fireEvent.keyDown(document, { key: 'Enter' })
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    const elsewhere = screen.getByRole('button', { name: 'Elsewhere' })
    elsewhere.focus()
    fireEvent.pointerDown(elsewhere)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    // The reader chose that spot: focus is not pulled back to the trigger.
    expect(elsewhere).toHaveFocus()
  })

  it('toggles from the trigger and hands a close() to function children', () => {
    const trigger = mount((close) => (
      <button type="button" onClick={close}>
        Done
      </button>
    ))
    fireEvent.click(trigger)
    fireEvent.click(trigger)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    fireEvent.click(trigger)
    fireEvent.click(screen.getByRole('button', { name: 'Done' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })
})
