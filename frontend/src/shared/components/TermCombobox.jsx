import { useId, useMemo, useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { Check, ChevronsUpDown, Loader2, Plus } from 'lucide-react'
import { cn } from '@/lib/utils'
import { TERM_MAX_LENGTH, termOptions } from '../utils/terms.js'
import Badge from './Badge.jsx'

/**
 * Picks a term from a list that filters as you type. Something that is not in the list shows up
 * as an "Add new" row; choosing it adds the term (`onCreate`) and selects it.
 */
export default function TermCombobox({ terms, value, onChange, onCreate, creating = false, ...inputProps }) {
  const listId = useId()
  const rootRef = useRef(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState(null) // null: show the chosen value; a string: the person is typing
  const [active, setActive] = useState(0)

  const options = useMemo(() => termOptions(terms, query ?? ''), [terms, query])

  const close = () => {
    setOpen(false)
    setQuery(null)
  }

  const choose = async (option) => {
    if (!option) return
    if (option.kind === 'new') {
      const stored = await onCreate(option.term)
      if (!stored) return // adding failed; the list stays open
      onChange(stored)
    } else {
      onChange(option.term)
    }
    close()
  }

  const move = (step) => {
    if (!options.length) return
    setOpen(true)
    setActive((current) => (current + step + options.length) % options.length)
  }

  const onKeyDown = (event) => {
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      move(1)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      move(-1)
    } else if (event.key === 'Enter' && open) {
      event.preventDefault() // never submits the form from here
      choose(options[active])
    } else if (event.key === 'Escape' && open) {
      event.preventDefault()
      close()
    }
  }

  // Close when focus leaves the whole control, not when it moves to a row.
  const onBlur = (event) => {
    if (!rootRef.current?.contains(event.relatedTarget)) close()
  }

  return (
    <div ref={rootRef} className="relative" onBlur={onBlur}>
      <input
        {...inputProps}
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && options[active] ? `${listId}-${active}` : undefined}
        autoComplete="off"
        value={query ?? value}
        maxLength={TERM_MAX_LENGTH}
        placeholder="Select or type a term"
        disabled={creating}
        onFocus={(event) => {
          setOpen(true)
          event.target.select()
        }}
        onChange={(event) => {
          setQuery(event.target.value)
          setActive(0)
          setOpen(true)
        }}
        onKeyDown={onKeyDown}
        className="flex h-9 w-full min-w-0 rounded-md border border-input bg-transparent px-3 py-1 pr-9 text-base shadow-xs outline-none transition-[color,box-shadow] placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:opacity-60 aria-invalid:border-destructive md:text-sm"
      />
      <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-muted-foreground">
        {creating ? (
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        ) : (
          <ChevronsUpDown className="h-4 w-4" aria-hidden="true" />
        )}
      </span>

      {open && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-60 w-full overflow-auto rounded-md border border-border bg-popover p-1 text-sm text-popover-foreground shadow-md"
        >
          {options.length === 0 && (
            <li className="px-2 py-2 text-muted-foreground">No terms yet. Type one to add it.</li>
          )}
          {options.map((option, index) => (
            <li
              key={`${option.kind}-${option.term}`}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={option.kind === 'term' && option.term === value}
              tabIndex={-1}
              // mousedown, not click: it runs before the input loses focus and closes the list
              onMouseDown={(event) => {
                event.preventDefault()
                choose(option)
              }}
              onMouseMove={() => setActive(index)}
              className={cn(
                'flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5',
                index === active && 'bg-accent text-accent-foreground',
              )}
            >
              {option.kind === 'new' ? (
                <>
                  <Plus className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="flex-1 truncate">{option.term}</span>
                  <Badge tone="primary">Add new</Badge>
                </>
              ) : (
                <>
                  <span className="flex-1 truncate">{option.term}</span>
                  {option.term === value && <Check className="h-4 w-4 shrink-0" aria-hidden="true" />}
                </>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

TermCombobox.propTypes = {
  terms: PropTypes.arrayOf(PropTypes.string).isRequired,
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  // Adds the term and resolves with its stored name, or with nothing if it could not be added.
  onCreate: PropTypes.func.isRequired,
  creating: PropTypes.bool,
}
