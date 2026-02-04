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
          gray: '#4a4a4a', // WCAG AA compliant (was #1a1a1a)
          primary: '#00ff41', // Matrix Green
          secondary: '#008f11',
          dim: 'rgba(0, 255, 65, 0.1)',
          border: '#333333',
          text: '#e0e0e0',
          muted: '#a0a0a0', // WCAG AA compliant (was #888888)
          danger: '#ff3333',
          warning: '#ffaa00'
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
