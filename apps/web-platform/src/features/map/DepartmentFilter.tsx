import { useTranslation } from 'react-i18next';
import type { DepartmentKey } from '../hospital/types';
import { DEPARTMENTS } from './departments';

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
      {DEPARTMENTS.map(({ key, ready }) => (
        <button
          key={key}
          type="button"
          className="dept-chip"
          aria-pressed={selected === key}
          disabled={!ready}
          title={ready ? undefined : t('dept.notReady')}
          onClick={() => onSelect(selected === key ? null : key)}
        >
          {t(`dept.${key}`)}
          {!ready && <small>{t('dept.notReady')}</small>}
        </button>
      ))}
    </div>
  );
}
