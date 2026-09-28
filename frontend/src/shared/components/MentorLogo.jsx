/**
 * SELVIA Brand Logo Component
 * Enterprise learning & monitoring platform mark with an intelligent AI core.
 */
export default function MentorLogo({
  size = 32,
  className = '',
  showText = false,
  textClassName = '',
  tagline = 'Engineering Workspace',
  showTagline = true,
  textColorClassName = '',
  capitalizeFirst = false,
}) {
  return (
    <div className={`inline-flex items-center gap-2.5 select-none ${className || 'text-current'}`}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 40 40"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0 transition-transform duration-200 hover:scale-105 text-current"
        aria-hidden="true"
      >
        {/* Outer Autonomous Agent Constellation Frame */}
        <path
          d="M20 4L35 12.5V27.5L20 36L5 27.5V12.5L20 4Z"
          className="stroke-current opacity-30"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Neural Network Connection Struts */}
        <line x1="20" y1="4" x2="20" y2="18" className="stroke-current opacity-35" strokeWidth="1.2" />
        <line x1="5" y1="12.5" x2="14" y2="18" className="stroke-current opacity-35" strokeWidth="1.2" />
        <line x1="35" y1="12.5" x2="26" y2="18" className="stroke-current opacity-35" strokeWidth="1.2" />

        {/* Geometric 'M' Architecture */}
        <path
          d="M10 29V15L20 24L30 15V29"
          className="stroke-current"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Constellation Nodes */}
        <circle cx="20" cy="4" r="2" className="fill-current" />
        <circle cx="35" cy="12.5" r="2" className="fill-current" />
        <circle cx="35" cy="27.5" r="2" className="fill-current" />
        <circle cx="20" cy="36" r="2" className="fill-current" />
        <circle cx="5" cy="27.5" r="2" className="fill-current" />
        <circle cx="5" cy="12.5" r="2" className="fill-current" />

        {/* AI Radiant Core Star */}
        <path
          d="M20 13L22 17L26 18L22 19L20 23L18 19L14 18L18 17L20 13Z"
          className="fill-primary"
        />
      </svg>

      {showText && (
        <div className={`flex flex-col leading-none ${textClassName}`}>
          <div className="flex items-baseline">
            <span
              className={`text-lg font-extrabold tracking-normal ${textColorClassName || 'text-blue-600'} ${
                capitalizeFirst ? 'capitalize' : ''
              }`}
            >
              selvia
            </span>
            <span className="px-0.5 text-xl font-black leading-none text-orange-500">
              .
            </span>
            <span className={`text-lg font-extrabold tracking-normal ${textColorClassName || 'text-blue-600'}`}>
              com
            </span>
          </div>
          {showTagline && tagline && (
            <span className="text-[10px] opacity-70 font-medium tracking-tight mt-0.5 hidden sm:inline">
              {tagline}
            </span>
          )}
        </div>
      )}
    </div>
  )
}
