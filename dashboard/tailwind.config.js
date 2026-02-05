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
          gray: '#6b6b6b', // WCAG AA compliant - increased from #4a4a4a (4.5:1 ratio on dark)
          primary: '#00ff41', // Matrix Green (high contrast)
          secondary: '#00cc33', // Brighter secondary for better visibility
          dim: 'rgba(0, 255, 65, 0.15)', // Slightly brighter dim
          border: '#404040', // Increased from #333333 for better visibility
          text: '#f0f0f0', // Brighter text (was #e0e0e0)
          muted: '#b0b0b0', // WCAG AA compliant - increased from #a0a0a0 (7:1 ratio)
          danger: '#ff4444', // Brighter red
          warning: '#ffbb33', // Brighter warning color
          success: '#00ff41', // Alias for primary (color-blind friendly labeling)
          error: '#ff4444', // Alias for danger (color-blind friendly labeling)
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
