/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        warm: {
          50:  "#fff8f1",
          100: "#feecdc",
          200: "#fcd9bd",
          300: "#fdba8c",
          400: "#ff8a4c",
          500: "#ff5a1f",
          600: "#d03801",
          700: "#b43403",
          800: "#8a2c0d",
          900: "#73230d",
        },
      },
      fontFamily: {
        sans: ["Noto Sans KR", "sans-serif"],
      },
      boxShadow: {
        // 따뜻한 톤이 살짝 도는 부드러운 그림자 (주황 계열 살짝 섞음)
        soft: "0 1px 2px rgba(208, 56, 1, 0.04), 0 4px 16px rgba(208, 56, 1, 0.06)",
        card: "0 1px 3px rgba(115, 35, 13, 0.05), 0 8px 24px -8px rgba(208, 56, 1, 0.10)",
        "card-hover": "0 2px 6px rgba(115, 35, 13, 0.06), 0 16px 36px -12px rgba(208, 56, 1, 0.16)",
        btn: "0 1px 2px rgba(115, 35, 13, 0.10), 0 4px 12px -2px rgba(208, 56, 1, 0.30)",
      },
      borderRadius: {
        "2xl": "1.125rem",
        "3xl": "1.5rem",
      },
      keyframes: {
        "fade-in-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-in-up": "fade-in-up 0.4s ease-out both",
      },
    },
  },
  plugins: [],
};
