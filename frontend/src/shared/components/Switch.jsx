import { useState } from 'react'
import { Switch as ShadcnSwitch } from '@/components/ui/switch'

export default function Switch({ defaultChecked = false, label, onChange }) {
  const [checked, setChecked] = useState(defaultChecked)

  function handleCheckedChange(val) {
    setChecked(val)
    if (onChange) onChange(val)
  }

  return (
    <label className="flex items-center justify-between py-2.5 gap-4 cursor-pointer">
      {label && <span className="text-sm font-medium text-foreground">{label}</span>}
      <ShadcnSwitch checked={checked} onCheckedChange={handleCheckedChange} />
    </label>
  )
}

