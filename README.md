# Iteration Project — Deployable Site

Everything in this folder is ready to push as a GitHub Pages site.

## Deploy

1. Create a new GitHub repository (any name; I'll call it `iterations` below).
2. In Terminal, cd into THIS folder and run:
   ```
   git init
   git add .
   git commit -m "initial"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/iterations.git
   git push -u origin main
   ```
3. On GitHub: Repo → Settings → Pages → Source: `main` branch, `/ (root)` folder.
4. Wait a minute. Visit `https://YOUR_USERNAME.github.io/iterations/`.

## Files

- `index.html` — landing page with the "begin" button
- `1.html` … `100.html` — 100 iteration pages with auto-advance and chain
- `data/1.csv` … `data/100.csv` — pixel data per iteration (cumulative)
- `qr/1.png` … `qr/100.png` — QR codes pointing to each iteration's page
- `spreadsheet_deltas.xlsx` — one workbook with 100 tabs, each containing only
  the pixels NEWLY added at that iteration. Upload to Google Drive, open with
  Google Sheets, and you have one Sheet with 100 tabs.

## QR codes

QR codes encode the URL `https://YOUR_USERNAME.github.io/iterations/N.html`. If your final GitHub Pages URL is
different, regenerate them by running:

   python generate_project.py --base-url https://YOUR_REAL_URL/

## How the chain works

- Visiting `1.html?play=1` starts an auto-advancing slideshow that ends at
  iteration 100, then returns to `index.html`.
- Visiting any single page (`47.html`) without `?play=1` shows a static view —
  this is what QR-code visitors see. They can click "play from here" to start
  the chain at that point.
- The autoadvance delay is 1.5 seconds per iteration. Edit the constant
  `AUTOADVANCE_DELAY_MS` in `generate_project.py` and regenerate to change.
