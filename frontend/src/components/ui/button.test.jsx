import { describe, expect, it } from 'vitest'
import { renderToStaticMarkup } from 'react-dom/server'
import { Button } from './button.jsx'

const html = (element) => renderToStaticMarkup(element)
// the class list always mentions "disabled:"; this looks for the attribute
const isDisabled = (markup) => / disabled=""/.test(markup)

describe('Button', () => {
  it('is an ordinary button when nothing is loading', () => {
    const markup = html(<Button>Save</Button>)
    expect(markup).toContain('Save')
    expect(markup).not.toContain('animate-spin')
    expect(markup).not.toContain('aria-busy')
    expect(isDisabled(markup)).toBe(false)
  })

  it('shows a spinning ring, is disabled and says it is busy while loading', () => {
    const markup = html(<Button loading>Save</Button>)
    expect(markup).toContain('animate-spin')
    expect(markup).toContain('aria-busy="true"')
    expect(isDisabled(markup)).toBe(true)
    expect(markup).toContain('Save')
  })

  it('shows only the ring on an icon button, in place of its icon', () => {
    const markup = html(
      <Button size="icon" loading aria-label="Send">
        <span>ICON</span>
      </Button>,
    )
    expect(markup).toContain('animate-spin')
    expect(markup).not.toContain('ICON')
  })

  it('stays disabled when told to, loading or not', () => {
    expect(isDisabled(html(<Button disabled>Save</Button>))).toBe(true)
  })
})
