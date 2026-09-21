import Card from './Card.jsx'
import './StatCard.css'

export default function StatCard({ icon: Icon, label, value, trend, tone = 'primary' }) {
  return (
    <Card className="stat-card">
      <div className={`stat-card__icon stat-card__icon--${tone}`}>
        <Icon size={20} strokeWidth={2} />
      </div>
      <div className="stat-card__body">
        <p className="stat-card__label">{label}</p>
        <p className="stat-card__value">{value}</p>
        {trend && <p className="stat-card__trend">{trend}</p>}
      </div>
    </Card>
  )
}
