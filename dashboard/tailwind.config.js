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
          gray: '#6b6b6b', // WCAG AA compliant (was #4a4a4a)
          primary: '#00ff41', // Matrix Green
          secondary: '#00cc33', // Brighter for visibility (was #008f11)
          dim: 'rgba(0, 255, 65, 0.15)', // Increased opacity (was 0.1)
          border: '#404040', // Better visibility (was #333333)
          text: '#f0f0f0', // Brighter (was #e0e0e0)
          muted: '#b0b0b0', // WCAG AA compliant (was #a0a0a0)
          danger: '#ff3333',
          warning: '#ffaa00',
          success: '#00ff41', // Alias for semantic usage
          error: '#ff4444',   // Alias for semantic usage
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
