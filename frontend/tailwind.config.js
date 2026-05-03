/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Minimal color palette
        background: '#0f172a',
        foreground: '#f8fafc',
        card: '#1e293b',
        'card-hover': '#334155',
        border: '#334155',
        'muted-text': '#94a3b8',
        'accent-blue': '#3b82f6',
        'accent-blue-hover': '#2563eb',
        'success': '#10b981',
        'error': '#ef4444',
      },
    },
  },
  plugins: [],
}
