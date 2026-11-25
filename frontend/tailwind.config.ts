import type { Config } from "tailwindcss";
const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0A0E17",
        surface: "#111827",
        card: "#121A2A",
        border: "#1E293B",
        muted: "#94A3B8",
        accent: "#3B82F6",
        profit: "#22C55E",
        loss: "#EF4444",
        warning: "#F59E0B",
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
export default config;
