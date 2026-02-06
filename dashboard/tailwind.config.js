/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          black: '#050505',
          dark: '#0a0a0a',
          card: '#0f0f0f',
          gray: '#7c7c7c', // WCAG AA: 4.84:1 on black, 4.55:1 on card (was #1a1a1a → #4a4a4a → #6b6b6b)
          primary: '#00ff41', // Matrix Green
          secondary: '#00cc33', // Brighter for better visibility (was #008f11)
          dim: 'rgba(0, 255, 65, 0.1)',
          border: '#5f5f5f', // WCAG AA: 3.01:1 on card (was #333333 → #404040 → #4d4d4d)
          text: '#f0f0f0', // Brighter text (was #e0e0e0)
          muted: '#b0b0b0', // WCAG AA: 9.40:1 contrast (was #888888 → #a0a0a0)
          danger: '#ff3333',
          warning: '#ffaa00',
          // Semantic aliases for color-blind friendliness
          success: '#00ff41',
          error: '#ff4444'
        }
      },
      fontFamily: {
        mono: ['"JetBrains Mono"', '"Fira Code"', '"Courier New"', 'monospace'],
      },
      boxShadow: {
        'glow': '0 0 10px rgba(0, 255, 65, 0.3)',
        'glow-lg': '0 0 20px rgba(0, 255, 65, 0.4)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
