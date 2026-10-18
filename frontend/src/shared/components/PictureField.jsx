import { useRef, useState } from 'react'
import PropTypes from 'prop-types'
import { Button } from '@/components/ui/button'
import { checkPictureFile, PICTURE_TYPES, squarePicture } from '../utils/image.js'
import Avatar from './Avatar.jsx'

/**
 * A picture with a button to choose another. The chosen file is cut to a square and shrunk here,
 * then handed to `onPick` as a small JPEG; sending it is up to the page (right away on the
 * profile, after the account exists during onboarding).
 */
export default function PictureField({ name, picture, onPick, onRemove, loading = false, size = 72 }) {
  const input = useRef(null)
  const [error, setError] = useState('')
  const [preparing, setPreparing] = useState(false)

  const choose = async (event) => {
    const file = event.target.files?.[0]
    event.target.value = '' // so the same file can be chosen again later
    const problem = checkPictureFile(file)
    if (problem) return setError(problem)
    setError('')
    setPreparing(true)
    try {
      await onPick(await squarePicture(file))
    } catch (failure) {
      setError(failure.message)
    } finally {
      setPreparing(false)
    }
  }

  return (
    <div className="flex items-center gap-4">
      <Avatar name={name} picture={picture} size={size} />
      <div className="grid gap-1.5">
        <div className="flex flex-wrap gap-2">
          <Button type="button" variant="outline" size="sm" loading={loading || preparing} onClick={() => input.current?.click()}>
            {picture ? 'Change picture' : 'Upload picture'}
          </Button>
          {onRemove && (
            <Button type="button" variant="ghost" size="sm" disabled={loading || preparing} onClick={onRemove}>
              Remove
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">JPG, PNG or WebP.</p>
        {error && (
          <p role="alert" className="text-xs text-destructive">
            {error}
          </p>
        )}
      </div>
      <input ref={input} type="file" accept={PICTURE_TYPES.join(',')} className="hidden" onChange={choose} />
    </div>
  )
}

PictureField.propTypes = {
  name: PropTypes.string,
  picture: PropTypes.string,
  onPick: PropTypes.func.isRequired,
  onRemove: PropTypes.func,
  loading: PropTypes.bool,
  size: PropTypes.number,
}
