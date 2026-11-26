import { useEffect, useId, useMemo, useRef, useState, type ReactNode } from 'react';
import { useTranslation } from 'react-i18next';
import { DEPARTMENTS, DISTRICTS } from './filters';
import { SUPPORT_LANGS, type SupportLang } from './languageSupport';
import { EMPTY_FILTERS, countMatches, filterCount, sameFilters, type SearchFilters } from './searchFilters';
import type { DepartmentKey, Hospital } from './types';

type PanelKey = 'dept' | 'district' | 'lang';

interface Props {
  hospitals: Hospital[];
  applied: SearchFilters;
  onApply: (f: SearchFilters) => void;
}

const toggle = <T,>(arr: T[], v: T): T[] => (arr.includes(v) ? arr.filter((x) => x !== v) : [...arr, v]);

// 병원 찾기 필터 바 — 진료 카테고리 / 지역 / 진료·상담 언어
// - 한 번에 패널 하나만 열림. 패널끼리 옮겨도 고른 조건(초안)은 유지, [병원 N곳 보기]를 눌러야 목록에 적용
// - 적용하지 않고 닫으면(같은 버튼·Esc·바깥 클릭) 초안은 적용된 조건으로 되돌림
// - 모바일(≤640px)은 같은 패널이 화면 아래 시트로 열리고 적용 버튼이 시트 하단에 고정 (styles.css)
export function HospitalFilterBar({ hospitals, applied, onApply }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<PanelKey | null>(null);
  const [draft, setDraft] = useState<SearchFilters>(applied);
  const [districtQuery, setDistrictQuery] = useState('');
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRefs = useRef<Partial<Record<PanelKey, HTMLButtonElement | null>>>({});
  const panelId = useId();

  // 주소가 바뀌어 적용 조건이 달라지면(뒤로 가기 등) 닫힌 상태의 초안도 맞춤
  useEffect(() => {
    if (!open) setDraft(applied);
  }, [applied, open]);

  const close = (focusBack = true) => {
    const was = open;
    setOpen(null);
    setDraft(applied);
    setDistrictQuery('');
    if (focusBack && was) triggerRefs.current[was]?.focus();
  };

  const openPanel = (key: PanelKey) => {
    if (open === key) return close();
    if (!open) setDraft(applied);
    setOpen(key);
  };

  // Esc · 바깥 클릭으로 닫기
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close();
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) close(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onDown);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onDown);
    };
  });

  const draftCount = useMemo(() => countMatches(hospitals, draft), [hospitals, draft]);
  const shown = open ? draft : applied;
  const dirty = !sameFilters(draft, applied);

  const apply = () => {
    onApply(draft);
    setOpen(null);
    setDistrictQuery('');
  };

  const deptLabel = (d: DepartmentKey) => t(`dept.${d}`);
  const districtLabel = (d: string) => t(`district.${d}`);
  const langLabel = (l: SupportLang) => t(`filter.langs.${l}`);

  const chipsOf = (f: SearchFilters) => [
    ...f.depts.map((d) => ({ key: `d-${d}`, label: deptLabel(d), without: { ...f, depts: f.depts.filter((x) => x !== d) } })),
    ...f.districts.map((d) => ({ key: `r-${d}`, label: districtLabel(d), without: { ...f, districts: f.districts.filter((x) => x !== d) } })),
    ...f.langs.map((l) => ({ key: `l-${l}`, label: langLabel(l), without: { ...f, langs: f.langs.filter((x) => x !== l) } })),
  ];

  const triggers: { key: PanelKey; label: string; count: number; icon: ReactNode }[] = [
    { key: 'dept', label: t('filter.dept'), count: shown.depts.length, icon: <StethoscopeIcon /> },
    { key: 'district', label: t('filter.district'), count: shown.districts.length, icon: <PinIcon /> },
    { key: 'lang', label: t('filter.lang'), count: shown.langs.length, icon: <ChatIcon /> },
  ];

  const q = districtQuery.trim().toLowerCase();
  const allLabel = t('filter.districtAll');
  const districtOptions = DISTRICTS.filter((d) => !q || districtLabel(d).toLowerCase().includes(q) || d.includes(q));
  const showAllOption = !q || allLabel.toLowerCase().includes(q);

  return (
    <div className="hf" ref={rootRef}>
      <div className="hf-bar" role="group" aria-label={t('filter.label')}>
        {triggers.map((tr) => (
          <button
            key={tr.key}
            ref={(el) => {
              triggerRefs.current[tr.key] = el;
            }}
            type="button"
            className="hf-trigger"
            aria-expanded={open === tr.key}
            aria-controls={open === tr.key ? panelId : undefined}
            onClick={() => openPanel(tr.key)}
          >
            <span className="hf-trigger-icon" aria-hidden="true">{tr.icon}</span>
            <span className="hf-trigger-label">
              {tr.label}
              {tr.count > 0 && <span className="hf-trigger-count"> ({tr.count})</span>}
            </span>
            <ChevronIcon />
          </button>
        ))}
      </div>

      {/* 닫혀 있을 때: 적용된 조건 칩 (× 누르면 바로 적용) */}
      {!open && filterCount(applied) > 0 && (
        <div className="hf-applied">
          <span className="hf-applied-label">{t('filter.applied')}</span>
          <Chips chips={chipsOf(applied)} onRemove={onApply} t={t} />
          <button type="button" className="hf-reset" onClick={() => onApply(EMPTY_FILTERS)}>
            {t('filter.reset')}
          </button>
        </div>
      )}

      {open && (
        <>
          <div className="hf-backdrop" onClick={() => close(false)} aria-hidden="true" />
          <div className="hf-panel" id={panelId} role="dialog" aria-label={triggers.find((x) => x.key === open)?.label}>
            <div className="hf-sheet-head">
              <div className="hf-sheet-tabs" role="tablist">
                {triggers.map((tr) => (
                  <button
                    key={tr.key}
                    type="button"
                    role="tab"
                    aria-selected={open === tr.key}
                    onClick={() => setOpen(tr.key)}
                  >
                    {tr.label}
                    {tr.count > 0 && ` (${tr.count})`}
                  </button>
                ))}
              </div>
              <button type="button" className="hf-sheet-close" onClick={() => close()} aria-label={t('filter.close')}>
                ×
              </button>
            </div>

            <div className="hf-body">
              {open === 'dept' && (
                <fieldset className="hf-fieldset">
                  <legend className="hf-title">{t('filter.deptTitle')}</legend>
                  <p className="hf-sub">{t('filter.multi')}</p>
                  <div className="hf-options">
                    {DEPARTMENTS.map((d) => (
                      <Check
                        key={d}
                        label={deptLabel(d)}
                        checked={draft.depts.includes(d)}
                        onChange={() => setDraft({ ...draft, depts: toggle(draft.depts, d) })}
                      />
                    ))}
                  </div>
                </fieldset>
              )}

              {open === 'district' && (
                <div className="hf-region">
                  <div className="hf-city">
                    <PinIcon />
                    {t('filter.city')}
                  </div>
                  <fieldset className="hf-fieldset">
                    <div className="hf-region-head">
                      <legend className="hf-title">{t('filter.districtTitle')}</legend>
                      <label className="hf-search">
                        <SearchIcon />
                        <span className="visually-hidden">{t('filter.districtSearch')}</span>
                        <input
                          type="search"
                          value={districtQuery}
                          placeholder={t('filter.districtSearch')}
                          onChange={(e) => setDistrictQuery(e.target.value)}
                        />
                      </label>
                    </div>
                    <div className="hf-options">
                      {showAllOption && (
                        <Check
                          label={allLabel}
                          checked={draft.districts.length === 0}
                          onChange={() => setDraft({ ...draft, districts: [] })}
                        />
                      )}
                      {districtOptions.map((d) => (
                        <Check
                          key={d}
                          label={districtLabel(d)}
                          checked={draft.districts.includes(d)}
                          onChange={() => setDraft({ ...draft, districts: toggle(draft.districts, d) })}
                        />
                      ))}
                    </div>
                    {!showAllOption && districtOptions.length === 0 && <p className="hf-sub">{t('filter.districtNone')}</p>}
                  </fieldset>
                </div>
              )}

              {open === 'lang' && (
                <fieldset className="hf-fieldset">
                  <legend className="hf-title">{t('filter.langTitle')}</legend>
                  <div className="hf-options hf-options-3">
                    {SUPPORT_LANGS.map((l) => (
                      <Check
                        key={l}
                        label={langLabel(l)}
                        checked={draft.langs.includes(l)}
                        onChange={() => setDraft({ ...draft, langs: toggle(draft.langs, l) })}
                      />
                    ))}
                  </div>
                  <p className="hf-note">{t('filter.langNote')}</p>
                  <p className="hf-note hf-note-sample">{t('filter.langSample')}</p>
                </fieldset>
              )}
            </div>

            <div className="hf-foot">
              <Chips chips={chipsOf(draft)} onRemove={setDraft} t={t} />
              <div className="hf-actions">
                {dirty && <span className="hf-dirty">{t('filter.notApplied')}</span>}
                <button type="button" className="hf-reset" onClick={() => setDraft(EMPTY_FILTERS)}>
                  {t('filter.reset')}
                </button>
                <button type="button" className="hf-apply" onClick={apply} disabled={draftCount === 0}>
                  {draftCount === 0 ? t('filter.noResult') : t('filter.apply', { count: draftCount })}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="hf-check">
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="hf-box" aria-hidden="true" />
      <span className="hf-check-label">{label}</span>
    </label>
  );
}

function Chips({
  chips,
  onRemove,
  t,
}: {
  chips: { key: string; label: string; without: SearchFilters }[];
  onRemove: (f: SearchFilters) => void;
  t: (k: string, o?: Record<string, unknown>) => string;
}) {
  if (chips.length === 0) return null;
  return (
    <ul className="hf-chips">
      {chips.map((c) => (
        <li key={c.key}>
          <button type="button" className="hf-chip" onClick={() => onRemove(c.without)} aria-label={t('filter.remove', { label: c.label })}>
            {c.label}
            <span aria-hidden="true">×</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

const svg = { width: 20, height: 20, viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', strokeWidth: 1.8, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const };

function StethoscopeIcon() {
  return (
    <svg {...svg}>
      <path d="M5 3v5a4 4 0 0 0 8 0V3" />
      <path d="M9 12v2a5 5 0 0 0 10 0v-2" />
      <circle cx="19" cy="10" r="2" />
    </svg>
  );
}
function PinIcon() {
  return (
    <svg {...svg}>
      <path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z" />
      <circle cx="12" cy="10" r="2.5" />
    </svg>
  );
}
function ChatIcon() {
  return (
    <svg {...svg}>
      <path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1.1-4.6A8 8 0 1 1 21 12z" />
      <path d="M8.5 12h.01M12 12h.01M15.5 12h.01" />
    </svg>
  );
}
function SearchIcon() {
  return (
    <svg {...svg} width={16} height={16} aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <path d="m20 20-3.5-3.5" />
    </svg>
  );
}
function ChevronIcon() {
  return (
    <svg {...svg} className="hf-chevron" aria-hidden="true">
      <path d="m6 9 6 6 6-6" />
    </svg>
  );
}
