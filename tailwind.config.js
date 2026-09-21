/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./apps/web/static/index.html', './apps/web/static/app.js'],
  theme: {
    extend: {
      colors: {
        ink: '#17202a',
        mint: '#136f63',
      },
      boxShadow: {
        panel: '0 12px 30px rgba(23, 32, 42, .06)',
      },
    },
  },
  plugins: [],
};
