import type { Config } from "tailwindcss";

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Editorial-clinical palette — deliberately not the Opus 4.7 default cream/serif house style
        bg: "#F4F1EB",            // warm parchment, slightly cooler than default cream
        surface: "#FBF9F4",
        ink: "#1A1B22",           // rich near-black with violet warmth
        muted: "#6B6F78",
        hairline: "#D6CFBE",
        oxblood: "#5E1A1A",       // deep hepatic burgundy — primary brand
        teal: "#0F4B4B",          // clinical deep teal — benign / positive
        amber: "#B8731F",         // VUS / caution
        coral: "#C44A3A",         // pathogenic / alert
        leaf: "#3B6B3F",          // benign accent
        ink2: "#2A2C36",
      },
      fontFamily: {
        display: ["Fraunces", "Georgia", "serif"],
        body: ["Geist", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
      boxShadow: {
        card: "0 1px 0 rgba(26,27,34,0.04), 0 8px 30px -12px rgba(94,26,26,0.10)",
        verdict: "0 30px 60px -30px rgba(94,26,26,0.35)",
      },
      backgroundImage: {
        grain: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.16  0 0 0 0 0.10  0 0 0 0 0.10  0 0 0 0.06 0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
} satisfies Config;
