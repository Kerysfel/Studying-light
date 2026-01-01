export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "var(--color-canvas)",
        "canvas-accent": "var(--color-canvas-accent)",
        surface: "var(--color-surface)",
        "surface-muted": "var(--color-surface-muted)",
        ink: "var(--color-ink)",
        muted: "var(--color-muted)",
        accent: "var(--color-accent)",
        "accent-deep": "var(--color-accent-deep)",
        slate: "var(--color-slate)",
        line: "var(--color-line)",
      },
      spacing: {
        "space-2xs": "var(--space-2xs)",
        "space-xs": "var(--space-xs)",
        "space-sm": "var(--space-sm)",
        "space-md": "var(--space-md)",
        "space-lg": "var(--space-lg)",
        "space-xl": "var(--space-xl)",
        "space-2xl": "var(--space-2xl)",
        "space-3xl": "var(--space-3xl)",
      },
      fontFamily: {
        sans: ["var(--font-sans)"],
        display: ["var(--font-display)"],
      },
      fontSize: {
        xs: ["var(--text-xs)", { lineHeight: "1.4" }],
        sm: ["var(--text-sm)", { lineHeight: "1.45" }],
        base: ["var(--text-md)", { lineHeight: "1.5" }],
        lg: ["var(--text-lg)", { lineHeight: "1.5" }],
        xl: ["var(--text-xl)", { lineHeight: "1.4" }],
        "2xl": ["var(--text-2xl)", { lineHeight: "1.3" }],
        "3xl": ["var(--text-3xl)", { lineHeight: "1.15" }],
      },
      boxShadow: {
        elevated: "var(--shadow-elevated)",
      },
    },
  },
  plugins: [],
};
