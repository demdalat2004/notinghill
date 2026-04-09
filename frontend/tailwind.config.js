/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        mono: ['"Share Tech Mono"', '"Courier New"', 'monospace'],
        display: ['"Orbitron"', 'monospace'],
        ui: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        // Dark theme (NSA/Hacker)
        nh: {
          bg0:    '#050a0f',
          bg1:    '#080e16',
          bg2:    '#0c1520',
          bg3:    '#111d2a',
          bg4:    '#162433',
          border: '#1a3344',
          border2:'#234455',
          text:   '#8bb8cc',
          text2:  '#5a8a9f',
          text3:  '#2a5a6f',
          cyan:   '#00e5ff',
          amber:  '#ffab00',
          green:  '#00e676',
          red:    '#ff4444',
          purple: '#b388ff',
          pink:   '#ff6090',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4,0,0.6,1) infinite',
        'scan': 'scan 4s linear infinite',
        'flicker': 'flicker 8s linear infinite',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'slide-in': 'slideIn 0.2s ease-out',
        'fade-in': 'fadeIn 0.3s ease-out',
      },
      keyframes: {
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        flicker: {
          '0%,100%': { opacity: '1' },
          '92%': { opacity: '1' },
          '93%': { opacity: '0.4' },
          '94%': { opacity: '1' },
          '96%': { opacity: '0.8' },
          '97%': { opacity: '1' },
        },
        glow: {
          from: { textShadow: '0 0 8px #00e5ff44' },
          to:   { textShadow: '0 0 20px #00e5ffaa, 0 0 40px #00e5ff44' },
        },
        slideIn: {
          from: { transform: 'translateX(100%)', opacity: '0' },
          to:   { transform: 'translateX(0)',    opacity: '1' },
        },
        fadeIn: {
          from: { opacity: '0', transform: 'translateY(4px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },
    },
  },
  plugins: [],
}
