import PropTypes from 'prop-types'

const MARK_SRC = '/selvia-mark.png'

export default function SelviaLogo({
  size = 32,
  className = '',
  showText = false,
  textClassName = '',
  tagline = 'Engineering Workspace',
  showTagline = true,
  textColorClassName = '',
}) {
  return (
    <div className={`inline-flex items-center gap-2.5 select-none ${className || 'text-current'}`}>
      <span
        className="relative shrink-0 overflow-hidden rounded-lg bg-zinc-950 ring-1 ring-cyan-400/25"
        style={{ width: size, height: size }}
        aria-hidden="true"
      >
        <img
          src={MARK_SRC}
          alt=""
          className="h-full w-full object-cover"
        />
      </span>

      {showText && (
        <div className={`flex flex-col leading-none ${textClassName}`}>
          <span
            className={`text-lg font-extrabold tracking-[0.2em] ${
              textColorClassName || 'text-foreground'
            }`}
          >
            SELVIA
          </span>
          {showTagline && tagline && (
            <span className="mt-0.5 hidden text-[10px] font-medium tracking-tight opacity-70 sm:inline">
              {tagline}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

SelviaLogo.propTypes = {
  size: PropTypes.number,
  className: PropTypes.string,
  showText: PropTypes.bool,
  textClassName: PropTypes.string,
  tagline: PropTypes.string,
  showTagline: PropTypes.bool,
  textColorClassName: PropTypes.string,
  capitalizeFirst: PropTypes.bool,
}
