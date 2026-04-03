import { useState, useEffect, useRef } from 'preact/compat';

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const paletteRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Toggle on Ctrl+K or ? (when not in an input)
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      } else if (e.key === '?' && !['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName ?? '')) {
        e.preventDefault();
        setIsOpen((prev) => !prev);
      }

      // Close on Esc
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen]);

  // Focus trap
  useEffect(() => {
    if (isOpen && paletteRef.current) {
      // Focus first element if any, else the palette itself
      const firstFocusable = paletteRef.current.querySelector<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      if (firstFocusable) {
        firstFocusable.focus();
      } else {
        paletteRef.current.focus();
      }
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 backdrop-blur-sm p-4">
      <div
        ref={paletteRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="command-palette-title"
        className="bg-white dark:bg-slate-900 w-full max-w-lg rounded-xl shadow-elevated border border-gray-200 dark:border-slate-800 overflow-hidden flex flex-col focus:outline-none"
        tabIndex={-1}
      >
        <div className="p-4 border-b border-gray-100 dark:border-slate-800 flex items-center justify-between">
          <h2 id="command-palette-title" className="text-lg font-semibold text-black dark:text-white">Keyboard Shortcuts</h2>
          <button
            onClick={() => setIsOpen(false)}
            className="p-1 rounded text-gray-500 hover:text-black dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Close dialog"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>

        <div className="p-4 flex-1 overflow-y-auto">
          <div className="space-y-4 text-sm">
            <div className="flex justify-between items-center py-2 border-b border-gray-50 dark:border-slate-800/50">
              <span className="text-gray-700 dark:text-gray-300">Open Command Palette / Help</span>
              <div className="flex gap-1">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">Ctrl</kbd>
                <span className="text-gray-500 dark:text-gray-400">+</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">K</kbd>
                <span className="mx-2 text-gray-400">or</span>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">?</kbd>
              </div>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-50 dark:border-slate-800/50">
              <span className="text-gray-700 dark:text-gray-300">Close Modals / Tooltips</span>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">Esc</kbd>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-50 dark:border-slate-800/50">
              <span className="text-gray-700 dark:text-gray-300">Navigate Heatmap</span>
              <div className="flex gap-1">
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">↑</kbd>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">↓</kbd>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">←</kbd>
                <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">→</kbd>
              </div>
            </div>

            <div className="flex justify-between items-center py-2 border-b border-gray-50 dark:border-slate-800/50">
              <span className="text-gray-700 dark:text-gray-300">Select Heatmap Cell</span>
              <kbd className="px-2 py-1 bg-gray-100 dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded font-mono text-xs text-black dark:text-white shadow-sm">Enter</kbd>
            </div>
          </div>
        </div>

        <div className="p-3 bg-gray-50 dark:bg-slate-800 text-xs text-center text-gray-500 dark:text-gray-400">
          Accessibility mode is always active. Use Tab to navigate through all interactive elements.
        </div>
      </div>
    </div>
  );
}
