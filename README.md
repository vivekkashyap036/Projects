# Cabo Scorekeeper

A clean, single-device scorekeeper for the card game Cabo, built with React, Vite, and Tailwind CSS.

## Features

- Add players and start a game with a configurable target score and failed-Cabo penalty
- Enter each player's hand total per round; automatically scores a successful Cabo call as 0 and a failed one with a penalty
- Live scoreboard with round-by-round history and running totals
- Full rules reference (`src/lib/rulesContent.js`) — edit if your table plays with house rules
- Game history saved on-device, across sessions
- Everything persists to `localStorage`, so a page refresh mid-game doesn't lose progress

## Development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

Outputs a static site in `dist/`, deployable to Vercel, Netlify, GitHub Pages, or any static host.

## Notes

This is a single-device, pass-the-phone scorekeeper — everyone enters their own hand total on one device while playing with physical cards. It does not sync across multiple devices.
