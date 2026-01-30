import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-geist-sans)', 'Inter', 'system-ui', 'sans-serif'],
        mono: ['var(--font-geist-mono)', 'Roboto Mono', 'monospace'],
      },
      colors: {
        background: "#000000",
        vercel: {
          border: "#333333",
          hover: "#444444",
          text: "#888888",
          primary: "#ffffff",
          secondary: "#111111",
        }
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
export default config;
