/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b0e14",
        panel: "#111722",
        line: "#232b38",
        accent: "#8b9cff",
      },
    },
  },
  plugins: [],
};
