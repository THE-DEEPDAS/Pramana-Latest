/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Light theme colors
        background: {
          light: '#ffffff',
          dark: '#0f172a',
          DEFAULT: '#ffffff',
        },
        foreground: {
          light: '#1f2937',
          dark: '#f8fafc',
          DEFAULT: '#1f2937',
        },
        card: {
          light: '#f3f4f6',
          dark: '#1e293b',
          DEFAULT: '#f3f4f6',
        },
        'card-hover': {
          light: '#e5e7eb',
          dark: '#334155',
          DEFAULT: '#e5e7eb',
        },
        border: {
          light: '#e5e7eb',
          dark: '#334155',
          DEFAULT: '#e5e7eb',
        },
        'muted-text': {
          light: '#6b7280',
          dark: '#94a3b8',
          DEFAULT: '#6b7280',
        },
        'accent-blue': {
          light: '#2563eb',
          dark: '#3b82f6',
          DEFAULT: '#2563eb',
        },
        'accent-blue-hover': {
          light: '#1d4ed8',
          dark: '#2563eb',
          DEFAULT: '#1d4ed8',
        },
        'success': '#10b981',
        'error': '#ef4444',
      },
    },
  },
  plugins: [],
}
