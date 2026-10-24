import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        term: {
          bg: "#0A0A0A",
          panel: "#0F0F10",
          panel2: "#141416",
          border: "#26262B",
          amber: "#FF8C00",
          gold: "#FFB400",
          up: "#2ECC71",
          down: "#FF3B3B",
          muted: "#9A9AA3",
          text: "#E6E6E6"
        }
      },
      fontFamily: {
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
        sans: ["ui-sans-serif", "system-ui", "sans-serif"]
      }
    }
  },
  plugins: []
} satisfies Config;
