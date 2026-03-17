/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        street: ["Bebas Neue", "system-ui", "sans-serif"],
        display: ["Syne", "system-ui", "sans-serif"],
        sans: ["Outfit", "DM Sans", "system-ui", "sans-serif"],
      },
      colors: {
        cypher: {
          bg: "#0a0a0f",
          surface: "#14141f",
          "surface-alt": "#1a1a2e",
          border: "#2a2a3e",
          muted: "#6b6b80",
          accent: "#a855f7",
          "accent-pink": "#ec4899",
          "accent-cyan": "#22d3ee",
          "accent-orange": "#f97316",
        },
        brand: {
          50: "#f5f3ff",
          100: "#ede9fe",
          200: "#ddd6fe",
          300: "#c4b5fd",
          400: "#a855f7",
          500: "#9333ea",
          600: "#7c3aed",
          700: "#6d28d9",
          800: "#5b21b6",
          900: "#4c1d95",
        },
      },
      boxShadow: {
        glow: "0 0 40px rgba(168, 85, 247, 0.3)",
        "glow-sm": "0 0 20px rgba(168, 85, 247, 0.2)",
        "card-dark": "0 4px 24px rgba(0,0,0,0.4)",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "slide-up": "slideUp 0.6s ease-out forwards",
        "slide-up-delay": "slideUp 0.6s ease-out 0.15s both",
        "slide-up-delay-2": "slideUp 0.6s ease-out 0.3s both",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      backgroundImage: {
        "gradient-mesh":
          "linear-gradient(135deg, rgba(168,85,247,0.15) 0%, transparent 50%), linear-gradient(225deg, rgba(236,72,153,0.1) 0%, transparent 50%)",
      },
    },
  },
  plugins: [],
};
