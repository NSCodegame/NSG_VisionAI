/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        tactical: {
          bg: "#05070a",
          surface: "rgba(15, 23, 42, 0.8)",
          cyan: "#00f2ff",
          blue: "#3b82f6",
          danger: "#f43f5e",
          warning: "#f59e0b",
          success: "#10b981",
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      boxShadow: {
        'glow-cyan': '0 0 15px rgba(0, 242, 255, 0.3)',
        'glow-danger': '0 0 15px rgba(244, 63, 94, 0.3)',
      }
    },
  },
  plugins: [],
}
