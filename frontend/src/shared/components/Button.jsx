import './Button.css'

/**
 * The one button every component should use, so a "primary action" looks the
 * same whether it's rendered from the planning module or the admin module.
 */
export default function Button({
  as: Component = 'button',
  variant = 'primary',
  size = 'md',
  icon: Icon,
  className = '',
  children,
  ...props
}) {
  const classes = ['btn', `btn--${variant}`, `btn--${size}`, className].filter(Boolean).join(' ')
  return (
    <Component className={classes} {...props}>
      {Icon && <Icon size={16} strokeWidth={2} />}
      {children}
    </Component>
  )
}
