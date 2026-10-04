/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        automotive: {
          50: '#f0f5fa',
          100: '#e1ecf5',
          200: '#c2d9eb',
          300: '#94bfde',
          400: '#5f9dcd',
          500: '#387fb8',
          600: '#27659a',
          700: '#21517d',
          800: '#1e4467',
          900: '#1d3a55',
          950: '#0e1c2b',
        },
        slate: {
          850: '#151e2e',
          900: '#0f172a',
          950: '#090d16',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Courier New', 'monospace'],
      },
    },
  },
  plugins: [],
}
