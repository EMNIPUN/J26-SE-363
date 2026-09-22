import { Button as ShadcnButton } from '@/components/ui/button'

const VARIANT_MAP = {
  primary: 'default',
  secondary: 'secondary',
  outline: 'outline',
  ghost: 'ghost',
  danger: 'destructive',
}

const SIZE_MAP = {
  sm: 'sm',
  md: 'default',
  lg: 'lg',
}

export default function Button({
  variant = 'primary',
  size = 'md',
  icon: Icon,
  className = '',
  children,
  ...props
}) {
  const mappedVariant = VARIANT_MAP[variant] || 'default'
  const mappedSize = SIZE_MAP[size] || 'default'

  return (
    <ShadcnButton
      variant={mappedVariant}
      size={mappedSize}
      className={`font-medium ${className}`}
      {...props}
    >
      {Icon && <Icon className="mr-1.5 h-4 w-4" />}
      {children}
    </ShadcnButton>
  )
}

