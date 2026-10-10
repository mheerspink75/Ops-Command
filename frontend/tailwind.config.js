/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: '#0f1117',
          raised: '#1a1d27',
          overlay: '#252836',
        },
        accent: {
          DEFAULT: '#6366f1',
          hover: '#818cf8',
        },
        severity: {
          sev1: '#ef4444',
          sev2: '#f97316',
          sev3: '#eab308',
          sev4: '#3b82f6',
        },
      },
    },
  },
  plugins: [],
}
