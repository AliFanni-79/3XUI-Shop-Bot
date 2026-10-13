/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Vazirmatn', 'system-ui', 'sans-serif'],
      },
      colors: {
        tg: {
          bg:         'var(--tg-theme-bg-color, #17212b)',
          secondary:  'var(--tg-theme-secondary-bg-color, #232e3c)',
          text:       'var(--tg-theme-text-color, #f5f5f5)',
          hint:       'var(--tg-theme-hint-color, #708499)',
          link:       'var(--tg-theme-link-color, #62bcf9)',
          button:     'var(--tg-theme-button-color, #2481cc)',
          buttonText: 'var(--tg-theme-button-text-color, #ffffff)',
          header:     'var(--tg-theme-header-bg-color, #17212b)',
          accent:     'var(--tg-theme-accent-text-color, #2481cc)',
        }
      }
    },
  },
  plugins: [],
}
