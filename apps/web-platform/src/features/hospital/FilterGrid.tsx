interface Option {
  value: string;
  label: string;
}

interface Props {
  label: string;
  allLabel: string;
  options: Option[];
  selected: string | null;
  onSelect: (value: string | null) => void;
}

// 병원 정보 페이지 위쪽의 표 모양 필터 (5칸씩 줄바꿈)
export function FilterGrid({ label, allLabel, options, selected, onSelect }: Props) {
  return (
    <div className="filter-grid" role="group" aria-label={label}>
      <button type="button" aria-pressed={selected === null} onClick={() => onSelect(null)}>
        {allLabel}
      </button>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={selected === o.value}
          onClick={() => onSelect(selected === o.value ? null : o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
