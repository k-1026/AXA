import { useTranslation } from 'react-i18next';
import type { DepartmentKey } from '../hospital/types';
import { DEPARTMENTS } from '../hospital/filters';

interface Props {
  selected: DepartmentKey | null;
  onSelect: (key: DepartmentKey | null) => void;
}

export function DepartmentFilter({ selected, onSelect }: Props) {
  const { t } = useTranslation();

  return (
    <div className="dept-filter" role="group" aria-label={t('dept.label')}>
      <button
        type="button"
        className="dept-chip"
        aria-pressed={selected === null}
        onClick={() => onSelect(null)}
      >
        {t('dept.all')}
      </button>
      {DEPARTMENTS.map((key) => (
        <button
          key={key}
          type="button"
          className="dept-chip"
          aria-pressed={selected === key}
          onClick={() => onSelect(selected === key ? null : key)}
        >
          {t(`dept.${key}`)}
        </button>
      ))}
    </div>
  );
}
