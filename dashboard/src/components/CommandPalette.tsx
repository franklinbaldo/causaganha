import { useState, useEffect, useRef } from 'preact/compat';

export function CommandPalette() {
  const [isOpen, setIsOpen] = useState<boolean>(false);
  const dialogRef = useRef<HTMLDialogElement>(null);

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

  // Sync dialog open state
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    if (isOpen && !dialog.open) {
      dialog.showModal();
    } else if (!isOpen && dialog.open) {
      dialog.close();
    }
  }, [isOpen]);

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby="command-palette-title"
      onClose={() => setIsOpen(false)}>
      <article>
        <header>
          <h2 id="command-palette-title">Keyboard Shortcuts</h2>
          <button
            className="outline"
            onClick={() => setIsOpen(false)}
            aria-label="Close dialog">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </header>

        <div>
          <div>
            <span>Open Command Palette / Help</span>
            <div>
              <kbd>Ctrl</kbd>
              <span>+</span>
              <kbd>K</kbd>
              <span>or</span>
              <kbd>?</kbd>
            </div>
          </div>

          <div>
            <span>Close Modals / Tooltips</span>
            <kbd>Esc</kbd>
          </div>

          <div>
            <span>Navigate Heatmap</span>
            <div>
              <kbd>↑</kbd>
              <kbd>↓</kbd>
              <kbd>←</kbd>
              <kbd>→</kbd>
            </div>
          </div>

          <div>
            <span>Select Heatmap Cell</span>
            <kbd>Enter</kbd>
          </div>
        </div>

        <footer>
          <small>Accessibility mode is always active. Use Tab to navigate through all interactive elements.</small>
        </footer>
      </article>
    </dialog>
  );
}
