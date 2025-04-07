/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/pages/**/*.{ts,tsx}", "./src/components/**/*.{ts,tsx}", "./src/app/**/*.{ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        chart: {
          1: "hsl(var(--chart-1))",
          2: "hsl(var(--chart-2))",
          3: "hsl(var(--chart-3))",
          4: "hsl(var(--chart-4))",
          5: "hsl(var(--chart-5))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: {
            height: 0,
          },
          to: {
            height: "var(--radix-accordion-content-height)",
          },
        },
        "accordion-up": {
          from: {
            height: "var(--radix-accordion-content-height)",
          },
          to: {
            height: 0,
          },
        },
        shimmer: {
          "0%": {
            "background-position": "-1000px 0",
          },
          "100%": {
            "background-position": "1000px 0",
          },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        shimmer: "shimmer 5s infinite linear",
      },
      backgroundImage: {
        "grid-slate-100": "linear-gradient(to right, #f1f5f9 1px, transparent 1px), linear-gradient(to bottom, #f1f5f9 1px, transparent 1px)",
        "grid-slate-800": "linear-gradient(to right, #1e293b 1px, transparent 1px), linear-gradient(to bottom, #1e293b 1px, transparent 1px)",
        "risk-pattern-red": "radial-gradient(circle at 30% 40%, rgba(239, 68, 68, 0.2) 5%, transparent 10%), radial-gradient(circle at 70% 60%, rgba(239, 68, 68, 0.2) 5%, transparent 10%)",
        "risk-pattern-amber": "radial-gradient(circle at 30% 40%, rgba(245, 158, 11, 0.15) 5%, transparent 10%), radial-gradient(circle at 70% 60%, rgba(245, 158, 11, 0.15) 5%, transparent 10%)",
        "risk-pattern-green": "radial-gradient(circle at 30% 40%, rgba(16, 185, 129, 0.15) 5%, transparent 10%), radial-gradient(circle at 70% 60%, rgba(16, 185, 129, 0.15) 5%, transparent 10%)",
        "rec-pattern": "radial-gradient(circle at 30% 40%, rgba(59, 130, 246, 0.15) 5%, transparent 10%), radial-gradient(circle at 70% 60%, rgba(59, 130, 246, 0.15) 5%, transparent 10%)",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
