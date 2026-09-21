import { useState } from 'react'
import './Switch.css'

export default function Switch({ defaultChecked = false, label }) {
  const [checked, setChecked] = useState(defaultChecked)
  return (
    <label className="switch-row">
      <span>{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        className={'switch' + (checked ? ' switch--on' : '')}
        onClick={() => setChecked((c) => !c)}
      >
        <span className="switch__thumb" />
      </button>
    </label>
  )
}
