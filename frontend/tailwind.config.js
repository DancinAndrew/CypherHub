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
          bg: "#0d0d14",
          surface: "#13131f",
          "surface-alt": "#1a1a2e",
          "surface-glass": "rgba(19,19,31,0.7)",
          border: "#2a2a45",
          "border-glow": "rgba(124,58,237,0.4)",
          muted: "#6b6b8a",
          accent: "#a855f7",
          "accent-bright": "#c084fc",
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
        glow: "0 0 40px rgba(168, 85, 247, 0.35)",
        "glow-sm": "0 0 20px rgba(168, 85, 247, 0.25)",
        "glow-lg": "0 0 60px rgba(168, 85, 247, 0.4)",
        "glow-cyan": "0 0 20px rgba(34, 211, 238, 0.3)",
        "glow-pink": "0 0 20px rgba(236, 72, 153, 0.3)",
        "card-dark": "0 4px 24px rgba(0,0,0,0.5)",
        "card-glass": "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
      },
      animation: {
        "fade-in": "fadeIn 0.5s ease-out forwards",
        "slide-up": "slideUp 0.6s ease-out forwards",
        "slide-up-delay": "slideUp 0.6s ease-out 0.15s both",
        "slide-up-delay-2": "slideUp 0.6s ease-out 0.3s both",
        "marquee": "marquee 25s linear infinite",
      },
      keyframes: {
        fadeIn: { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(24px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
      },
      backgroundImage: {
        "gradient-mesh":
          "linear-gradient(135deg, rgba(124,58,237,0.2) 0%, transparent 50%), linear-gradient(225deg, rgba(236,72,153,0.12) 0%, transparent 50%)",
        "gradient-radial-purple":
          "radial-gradient(ellipse 80% 50% at 50% -20%, rgba(124,58,237,0.3), transparent)",
        "gradient-card":
          "linear-gradient(135deg, rgba(255,255,255,0.05) 0%, rgba(255,255,255,0) 100%)",
      },
      backdropBlur: {
        xs: "4px",
      },
    },
  },
  plugins: [],
};
