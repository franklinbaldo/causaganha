import '@testing-library/jest-dom';

// Polyfill Web Animations API (element.animate) for jsdom — used by Svelte transitions
if (typeof Element !== 'undefined' && !Element.prototype.animate) {
  Element.prototype.animate = () =>
    ({ cancel: () => {}, finish: () => {}, addEventListener: () => {} }) as unknown as Animation;
}
