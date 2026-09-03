import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    screens: {
      sm: "768px",
      md: "800px",
      lg: "1200px",
      xl: "1440px",
    },
    extend: {
      fontFamily: {
        display: [
          "'TASA Orbiter Display SemiBold'",
          "'TASA Orbiter Display SemiBold Placeholder'",
          "sans-serif",
        ],
        heading: [
          "'TASA Orbiter Display SemiBold'",
          "'TASA Orbiter Display SemiBold Placeholder'",
          "sans-serif",
        ],
        body: ["'Inter'", "'Inter Placeholder'", "sans-serif"],
        sans: ["'Inter'", "'Inter Placeholder'", "sans-serif"],
        mono: ["'Menlo'", "monospace"],
      },
      fontSize: {
        display: ["32px", { lineHeight: "1.19", fontWeight: "400" }],
        heading: ["24px", { lineHeight: "1.33", fontWeight: "400" }],
        body: ["16px", { lineHeight: "1.5", fontWeight: "700" }],
        mono: ["18px", { lineHeight: "1.5", fontWeight: "400" }],
        // Helper scales aligned with base line-heights
        h1: ["32px", { lineHeight: "1.19", fontWeight: "400" }],
        h2: ["24px", { lineHeight: "1.33", fontWeight: "400" }],
        h3: ["20px", { lineHeight: "1.33", fontWeight: "400" }],
        h4: ["18px", { lineHeight: "1.33", fontWeight: "400" }],
        sm: ["14px", { lineHeight: "1.5", fontWeight: "700" }],
        xs: ["12px", { lineHeight: "1.5", fontWeight: "700" }],
      },
      colors: {
        // Razorpay design system tokens
        text: {
          DEFAULT: "#000000",
          muted: "#0000ee",
        },
        accent: {
          DEFAULT: "#305eff",
          foreground: "#ffffff",
        },
        primary: {
          DEFAULT: "#0000ee",
          foreground: "#ffffff",
        },
        surface: {
          DEFAULT: "#305eff",
          foreground: "#ffffff",
        },
        background: "#ffffff",
        "on-primary": "#ffffff",
        "text-muted": "#0000ee",

        // Shadcn UI Semantic Mappings
        foreground: "#000000",
        card: {
          DEFAULT: "#ffffff",
          foreground: "#000000",
        },
        popover: {
          DEFAULT: "#ffffff",
          foreground: "#000000",
        },
        muted: {
          DEFAULT: "#ffffff",
          foreground: "#0000ee",
        },
        border: "rgba(0, 0, 0, 0.12)",
        input: "rgba(0, 0, 0, 0.2)",
        ring: "#305eff",
        destructive: {
          DEFAULT: "#ef4444",
          foreground: "#ffffff",
        },
      },
      borderRadius: {
        sm: "2px",
        md: "4px",
        lg: "8px",
        xl: "12px",
        card: "12px",
        button: "8px",
      },
      boxShadow: {
        card: "rgba(0, 0, 0, 0.04) 0px -2px 4px 0px",
        elevated: "rgba(25, 40, 57, 0.09) 0px 2px 16px 0px",
      },
      spacing: {
        1: "4px",
        2: "8px",
        3: "12px",
        4: "16px",
        5: "20px",
        6: "24px",
        22: "88px",
        section: "88px",
      },
      transitionTimingFunction: {
        DEFAULT: "ease",
        ease: "ease",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
