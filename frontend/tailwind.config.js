/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        "brand-green": "#00A86B",
        "brand-green-light": "#E8F8F2",
        "bg": "#F8F8F6",
        "card-bg": "#FFFFFF",
        "text-primary": "#1A1A1A",
        "text-secondary": "#6B6B6B",
        "hot": "#E24B4A",
        "warm": "#BA7517",
        "cool": "#888780",
      },
      fontFamily: {
        sans: ["DM Sans", "sans-serif"],
        heading: ["Playfair Display", "serif"],
      },
      borderRadius: {
        DEFAULT: "10px",
      },
    },
  },
  plugins: [],
}

