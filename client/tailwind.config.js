/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        rail: {
          dark: '#080C14',
          card: '#0F1626',
          cardLight: '#151F33',
          border: 'rgba(255, 255, 255, 0.08)',
          accent: '#3B82F6',
          emerald: '#10B981',
          amber: '#F59E0B',
          rose: '#F43F5E',
          cyan: '#06B6D4',
        }
      },
      fontFamily: {
        sans: ['Inter', 'Outfit', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'glow-pulse': 'glow 2.5s ease-in-out infinite alternate',
      },
      keyframes: {
        glow: {
          '0%': { boxShadow: '0 0 15px -3px rgba(16, 185, 129, 0.3)' },
          '100%': { boxShadow: '0 0 25px 4px rgba(16, 185, 129, 0.6)' },
        }
      }
    },
  },
  plugins: [],
}
