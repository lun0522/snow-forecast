import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Info } from "lucide-react";

interface TermTooltipProps {
  label: string;
  tooltip: ReactNode;
}

interface PopoverPos {
  left: number;
  top: number;
  placement: "bottom" | "top";
}

const POPOVER_HALF_WIDTH = 144;
const VIEWPORT_MARGIN = 12;

/** Inline dotted-underlined term trigger that opens a portal tooltip above/below without table clipping. */
export function TermTooltip({ label, tooltip }: TermTooltipProps) {
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const [pos, setPos] = useState<PopoverPos | null>(null);
  const tooltipId = useId();

  const openPopover = () => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const minCenter = VIEWPORT_MARGIN + POPOVER_HALF_WIDTH;
    const maxCenter = Math.max(minCenter, vw - VIEWPORT_MARGIN - POPOVER_HALF_WIDTH);
    const left = Math.max(minCenter, Math.min(maxCenter, rect.left + rect.width / 2));
    const preferTop = rect.bottom + 180 > vh && rect.top > 160;
    setPos({
      left,
      top: preferTop ? rect.top - 8 : rect.bottom + 8,
      placement: preferTop ? "top" : "bottom",
    });
  };

  const closePopover = () => setPos(null);

  useEffect(() => {
    if (!pos) return;
    const handleDismiss = () => setPos(null);
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPos(null);
    };
    window.addEventListener("scroll", handleDismiss, { passive: true, capture: true });
    window.addEventListener("resize", handleDismiss, { passive: true });
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("scroll", handleDismiss, true);
      window.removeEventListener("resize", handleDismiss);
      window.removeEventListener("keydown", handleKey);
    };
  }, [pos]);

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-describedby={pos ? tooltipId : undefined}
        onMouseEnter={openPopover}
        onMouseLeave={closePopover}
        onFocus={openPopover}
        onBlur={closePopover}
        className="inline-flex cursor-help items-center gap-1 border-b border-dotted border-slate-400/80 pb-px font-medium [letter-spacing:inherit] [text-transform:inherit] text-inherit transition hover:border-sky-500 hover:text-slate-900 focus:border-sky-500 focus:text-slate-900 focus:outline-none dark:border-slate-500 dark:hover:border-sky-400 dark:hover:text-white dark:focus:border-sky-400 dark:focus:text-white"
      >
        <span>{label}</span>
        <Info className="h-3 w-3 shrink-0 opacity-65" />
      </button>

      {pos &&
        createPortal(
          <div
            id={tooltipId}
            role="tooltip"
            style={{
              left: pos.left,
              top: pos.top,
              transform: pos.placement === "top" ? "translate(-50%, -100%)" : "translateX(-50%)",
            }}
            className="pointer-events-none fixed z-50 w-72 max-w-[calc(100vw-24px)] rounded-lg border border-slate-200/95 bg-white px-3 py-2 text-left text-xs font-normal normal-case leading-relaxed tracking-normal text-slate-700 shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
          >
            {tooltip}
          </div>,
          document.body,
        )}
    </>
  );
}
