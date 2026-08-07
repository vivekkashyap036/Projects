# Resume

A responsive resume/CV web app built with React, Vite, and Tailwind CSS.

## Editing your resume

All resume content lives in one place: [`src/data/resume.js`](src/data/resume.js). Update the `name`, `title`, `experience`, `education`, `skills`, `extracurricular`, and `languages` fields with your own details — the UI updates automatically.

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

## Export to PDF

Click "Save as PDF" in the app, which opens the browser print dialog (styled for a clean, one-page print layout).
