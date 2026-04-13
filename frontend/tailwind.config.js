/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,jsx,ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        // Deep navy base
        navy: {
          950: '#060a14',
          900: '#0a0e1a',
          800: '#0d1526',
          700: '#111c33',
          600: '#172040',
        },
        // Electric blue accent
        accent: {
          blue:   '#3b82f6',
          violet: '#8b5cf6',
          teal:   '#14b8a6',
          cyan:   '#06b6d4',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      backgroundImage: {
        'gradient-brand': 'linear-gradient(135deg, #3b82f6 0%, #8b5cf6 50%, #14b8a6 100%)',
        'gradient-card':  'linear-gradient(145deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':    'fadeIn 0.3s ease-in-out',
        'slide-in':   'slideIn 0.3s ease-out',
        'shimmer':    'shimmer 1.6s linear infinite',
      },
      keyframes: {
        fadeIn:  { '0%': { opacity: '0' },                  '100%': { opacity: '1' } },
        slideIn: { '0%': { opacity: '0', transform: 'translateY(8px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        shimmer: { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
      },
      backdropBlur: {
        xs: '2px',
      },
    },
  },
  plugins: [],
}
