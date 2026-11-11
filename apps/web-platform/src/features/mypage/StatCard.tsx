import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRightIcon } from './icons';

interface Props {
  to: string;
  label: string;
  value: number;
  icon: ReactNode;
  tone: 'blue' | 'orange' | 'green';
}

export function StatCard({ to, label, value, icon, tone }: Props) {
  return (
    <Link to={to} className="mp-card mp-stat">
      <span className={`mp-stat-icon tone-${tone}`}>{icon}</span>
      <span className="mp-stat-text">
        <span className="mp-stat-label">{label}</span>
        <strong className="mp-stat-value">{value}</strong>
      </span>
      <span className="mp-chevron">
        <ChevronRightIcon />
      </span>
    </Link>
  );
}
