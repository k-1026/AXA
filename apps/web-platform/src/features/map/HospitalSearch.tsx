import { useId, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useHospitalName } from '../hospital/name';
import type { Hospital } from '../hospital/types';

// 띄어쓰기·대소문자 무시하고 한국어·영어 이름 둘 다에서 찾는다
const norm = (s: string) => s.replace(/\s+/g, '').toLowerCase();

export function matchHospitals(items: Hospital[], query: string) {
  const q = norm(query);
  if (!q) return [];
  return items.filter((h) => norm(h.name).includes(q) || norm(h.nameEn).includes(q));
}

interface Props {
  hospitals: Hospital[];
  /** 검색 결과 (null이면 검색 해제) */
  onSearch: (result: Hospital[] | null) => void;
}

const MAX_SUGGESTIONS = 8;

export function HospitalSearch({ hospitals, onSearch }: Props) {
  const { t } = useTranslation();
  const nameOf = useHospitalName();
  const listId = useId();
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);

  const matches = useMemo(() => matchHospitals(hospitals, query), [hospitals, query]);
  // 자동완성은 가나다순 (순위·추천 정렬 없음, docs/compliance.md)
  const suggestions = useMemo(
    () => [...matches].sort((a, b) => nameOf(a).localeCompare(nameOf(b))).slice(0, MAX_SUGGESTIONS),
    [matches, nameOf],
  );

  const submit = (e: FormEvent) => {
    e.preventDefault();
    setOpen(false);
    onSearch(query.trim() ? matches : null);
  };

  const pick = (h: Hospital) => {
    setQuery(nameOf(h));
    setOpen(false);
    onSearch([h]);
  };

  const clear = () => {
    setQuery('');
    setOpen(false);
    onSearch(null);
  };

  return (
    <form className="map-search" role="search" onSubmit={submit}>
      <input
        type="search"
        value={query}
        placeholder={t('map.searchPlaceholder')}
        aria-label={t('map.searchLabel')}
        role="combobox"
        aria-expanded={open && suggestions.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          if (!e.target.value) onSearch(null);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => e.key === 'Escape' && setOpen(false)}
      />
      {query && (
        <button type="button" className="map-search-clear" onClick={clear} aria-label={t('map.searchClear')}>
          ×
        </button>
      )}
      <button type="submit" className="map-search-submit" aria-label={t('map.searchLabel')}>
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="round" aria-hidden="true">
          <circle cx="10.5" cy="10.5" r="6.5" />
          <path d="m15.5 15.5 5 5" />
        </svg>
      </button>

      {open && query.trim() && (
        <ul id={listId} className="map-search-list" role="listbox">
          {suggestions.length ? (
            suggestions.map((h) => (
              <li key={h.id} role="option" aria-selected={false}>
                {/* onMouseDown: input blur보다 먼저 처리 */}
                <button type="button" onMouseDown={(e) => e.preventDefault()} onClick={() => pick(h)}>
                  <strong>{nameOf(h)}</strong>
                  <span>{h.addr}</span>
                </button>
              </li>
            ))
          ) : (
            <li className="map-search-empty">{t('map.searchEmpty')}</li>
          )}
          {matches.length > MAX_SUGGESTIONS && (
            <li className="map-search-more">{t('map.searchMore', { count: matches.length })}</li>
          )}
        </ul>
      )}
    </form>
  );
}
