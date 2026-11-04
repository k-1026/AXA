import { useEffect, useRef, useState } from 'react';
import { MoreIcon } from './icons';

interface Props {
  label: string; // 버튼 이름 (읽기 프로그램용)
  items: { label: string; danger?: boolean; onSelect: () => void }[];
}

// "…" 버튼과 작은 메뉴. 바깥을 누르거나 Esc를 누르면 닫힌다
export function MoreMenu({ label, items }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: Event) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('pointerdown', close);
    document.addEventListener('keydown', close);
    return () => {
      document.removeEventListener('pointerdown', close);
      document.removeEventListener('keydown', close);
    };
  }, [open]);

  return (
    <div className="chat-more" ref={ref}>
      <button
        type="button"
        className="chat-icon-button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={(e) => {
          e.stopPropagation();
          setOpen(!open);
        }}
      >
        <MoreIcon />
      </button>
      {open && (
        <ul className="chat-more-menu" role="menu">
          {items.map((it) => (
            <li key={it.label} role="none">
              <button
                type="button"
                role="menuitem"
                className={it.danger ? 'is-danger' : undefined}
                onClick={(e) => {
                  e.stopPropagation();
                  setOpen(false);
                  it.onSelect();
                }}
              >
                {it.label}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
