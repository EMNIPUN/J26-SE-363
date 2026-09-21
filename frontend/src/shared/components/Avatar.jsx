import './Avatar.css'

function getInitials(name = '') {
  return name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('')
}

export default function Avatar({ name, size = 36 }) {
  return (
    <div className="avatar" style={{ width: size, height: size, fontSize: size * 0.4 }}>
      {getInitials(name)}
    </div>
  )
}
