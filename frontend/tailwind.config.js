/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
          950: '#082f49',
        },
        genome: {
          a: '#e74c3c',  // Adenine - Red
          t: '#2ecc71',  // Thymine - Green
          g: '#3498db',  // Guanine - Blue
          c: '#f1c40f',  // Cytosine - Yellow
        },
        impact: {
          high: '#dc2626',
          moderate: '#f59e0b',
          low: '#3b82f6',
          modifier: '#6b7280',
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Monaco', 'monospace'],
      },
    },
  },
  plugins: [],
}
