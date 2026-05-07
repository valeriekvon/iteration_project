"""
generate_project.py
--------------------
Build the complete iteration website from a source RGB CSV.

Outputs a deployable folder with:
- 100 cumulative CSV files (one per iteration)
- 100 HTML pages with chain-navigation and auto-advance
- One xlsx file with 100 tabs (each containing only that iteration's NEW pixels)
- 100 QR codes (PNG)
- index.html landing page
- README.md with deploy instructions
"""
import argparse
import csv
import random
from pathlib import Path

import openpyxl
import qrcode

# -------- defaults --------
NUM_ITERATIONS = 100
RANDOM_SEED = 42
AUTOADVANCE_DELAY_MS = 1500
QUOTE_TEXT = (
    'A photograph of a publication containing the line: '
    '"We believe that technology is at its very best when it is invisible."'
)


def load_pixels(csv_path):
    pixels = []
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            pixels.append((
                int(row['x']),
                int(row['y']),
                int(row['R']),
                int(row['G']),
                int(row['B']),
            ))
    return pixels


def shuffle_pixels(pixels, seed):
    rng = random.Random(seed)
    p = pixels.copy()
    rng.shuffle(p)
    return p


def get_dims(pixels):
    return max(p[0] for p in pixels) + 1, max(p[1] for p in pixels) + 1


def write_iteration_csvs(shuffled, num_it, out_dir):
    """Write delta CSVs — each contains ONLY the new pixels for that iteration.
    Browser-side, each HTML page loads deltas 1..N in parallel; with caching,
    moving through the chain only ever fetches one new file per step."""
    data_dir = out_dir / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    total = len(shuffled)
    prev = 0
    for i in range(1, num_it + 1):
        n = round(total * i / num_it)
        delta = shuffled[prev:n]
        prev = n
        with open(data_dir / f'{i}.csv', 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['x', 'y', 'R', 'G', 'B'])
            w.writerows(delta)


def write_delta_xlsx(shuffled, num_it, out_dir):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    total = len(shuffled)
    prev = 0
    for i in range(1, num_it + 1):
        n = round(total * i / num_it)
        delta = shuffled[prev:n]
        prev = n
        ws = wb.create_sheet(f'iter_{i:03d}')
        ws.append(['x', 'y', 'R', 'G', 'B'])
        for px in delta:
            ws.append(list(px))
    wb.save(out_dir / 'spreadsheet_deltas.xlsx')


ITERATION_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>iteration {n} of {total}</title>
<style>
  body {{ background:#fff; color:#222; font-family:'Helvetica Neue',Arial,sans-serif;
          margin:0; padding:30px; max-width:1200px; }}
  h1 {{ margin:0 0 4px; font-size:13px; font-weight:normal;
        letter-spacing:0.08em; text-transform:uppercase; }}
  #subtitle {{ margin:0 0 24px; font-size:12px; color:#888; }}
  canvas {{ display:block; max-width:100%; height:auto;
            image-rendering:pixelated; background:#fff; border:1px solid #eee; }}
  nav {{ margin-top:18px; font-size:12px; }}
  nav a {{ color:#222; text-decoration:none; margin-right:10px; padding:6px 12px;
          border:1px solid #ccc; display:inline-block; }}
  nav a:hover {{ background:#222; color:#fff; }}
  .progress {{ margin-top:18px; font-family:monospace; font-size:11px; color:#888; }}
  .progress .bar {{ display:inline-block; width:200px; height:4px; background:#eee;
                    vertical-align:middle; margin:0 10px; }}
  .progress .fill {{ display:block; height:100%; background:#222; }}
</style>
</head>
<body>
  <h1>iteration {n} / {total}</h1>
  <p id="subtitle">{percent}% rendered · {n_pixels:,} of {total_pixels:,} pixels</p>
  <canvas id="canvas" width="{width}" height="{height}"></canvas>
  <nav>
    {prev_link}
    {next_link}
    <a href="index.html">index</a>
    <a href="?play=1">play from here</a>
  </nav>
  <p class="progress">
    [<span class="bar"><span class="fill" style="width:{percent}%"></span></span>] {percent}%
  </p>

<script>
const ITERATION = {n};
const TOTAL = {total};
const WIDTH = {width};
const HEIGHT = {height};
const AUTOADVANCE_MS = {advance_ms};

async function loadAndRender() {{
  const canvas = document.getElementById('canvas');
  const ctx = canvas.getContext('2d');
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, WIDTH, HEIGHT);
  const img = ctx.getImageData(0, 0, WIDTH, HEIGHT);

  // fetch all deltas from 1 to ITERATION in parallel
  // (browser caches these — chain animation only fetches one new file per step)
  const promises = [];
  for (let i = 1; i <= ITERATION; i++) {{
    promises.push(fetch('data/' + i + '.csv').then(r => r.text()));
  }}
  const texts = await Promise.all(promises);

  // accumulate all delta pixels (order is irrelevant — they don't overlap)
  for (const text of texts) {{
    const lines = text.split('\\n');
    for (let i = 1; i < lines.length; i++) {{
      const ln = lines[i].trim();
      if (!ln) continue;
      const p = ln.split(',');
      if (p.length < 5) continue;
      const idx = (+p[1] * WIDTH + +p[0]) * 4;
      img.data[idx] = +p[2];
      img.data[idx+1] = +p[3];
      img.data[idx+2] = +p[4];
      img.data[idx+3] = 255;
    }}
  }}
  ctx.putImageData(img, 0, 0);

  const params = new URLSearchParams(window.location.search);
  if (params.has('play')) {{
    const next = ITERATION + 1;
    const target = next > TOTAL ? 'index.html' : next + '.html?play=1';
    setTimeout(() => {{ window.location = target; }}, AUTOADVANCE_MS);
  }}
}}
loadAndRender();
</script>
</body>
</html>"""


def write_html_pages(shuffled, num_it, w, h, out_dir):
    total_pixels = len(shuffled)
    for i in range(1, num_it + 1):
        n_pixels = round(total_pixels * i / num_it)
        percent = round(i * 100 / num_it)
        prev_link = f'<a href="{i-1}.html">← prev</a>' if i > 1 else ''
        next_link = f'<a href="{i+1}.html">next →</a>' if i < num_it else '<a href="index.html">end</a>'
        html = ITERATION_HTML.format(
            n=i, total=num_it, percent=percent,
            n_pixels=n_pixels, total_pixels=total_pixels,
            width=w, height=h,
            prev_link=prev_link, next_link=next_link,
            advance_ms=AUTOADVANCE_DELAY_MS,
        )
        with open(out_dir / f'{i}.html', 'w') as f:
            f.write(html)


INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>iteration project</title>
<style>
  body {{ font-family:'Helvetica Neue',Arial,sans-serif; max-width:640px;
          margin:60px auto; padding:0 24px; line-height:1.5; color:#222; }}
  h1 {{ font-size:14px; font-weight:normal; letter-spacing:0.08em;
        text-transform:uppercase; margin-bottom:24px; }}
  p {{ font-size:14px; }}
  a.start {{ display:inline-block; padding:10px 20px; background:#222; color:#fff;
            text-decoration:none; margin:20px 0; font-size:13px;
            letter-spacing:0.05em; text-transform:uppercase; }}
  a.start:hover {{ background:#444; }}
  .grid {{ display:grid; grid-template-columns:repeat(10,1fr); gap:3px; margin:30px 0; }}
  .grid a {{ display:flex; align-items:center; justify-content:center;
            aspect-ratio:1; background:#f4f4f4; font-size:10px; color:#666;
            text-decoration:none; }}
  .grid a:hover {{ background:#222; color:#fff; }}
  .meta {{ margin-top:30px; font-size:11px; color:#888; line-height:1.6; }}
</style>
</head>
<body>
  <h1>One image · One hundred iterations</h1>
  <p>{quote}</p>
  <p>Below: one hundred steps reconstructing the image from a spreadsheet
     of pixel values. Each iteration adds 1% of the data.
     Click <em>begin</em> to play the chain as a slow animation, or pick any
     iteration directly to view it as a static page.</p>
  <a class="start" href="1.html?play=1">begin →</a>
  <div class="grid">
    {grid}
  </div>
  <p class="meta">
    The image is sourced from a single Canon RAW file, demosaiced and quantised
    to 8-bit RGB. Pixels were shuffled with a fixed seed and divided into 100
    equal cumulative sets. The corresponding spreadsheet
    (<code>spreadsheet_deltas.xlsx</code>) contains 100 tabs, each holding only
    the new pixels added at that iteration. QR codes for each iteration are in
    the <code>qr/</code> folder for use in the printed publication.
  </p>
</body>
</html>"""


def write_index(num_it, out_dir):
    grid = ''.join([f'<a href="{i}.html">{i}</a>' for i in range(1, num_it + 1)])
    with open(out_dir / 'index.html', 'w') as f:
        f.write(INDEX_HTML.format(grid=grid, quote=QUOTE_TEXT))


def write_qr_codes(num_it, base_url, out_dir):
    qr_dir = out_dir / 'qr'
    qr_dir.mkdir(exist_ok=True)
    base = base_url.rstrip('/')
    for i in range(1, num_it + 1):
        qrcode.make(f'{base}/{i}.html').save(qr_dir / f'{i}.png')


README = """# Iteration Project — Deployable Site

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

QR codes encode the URL `{base_url}/N.html`. If your final GitHub Pages URL is
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
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source_csv')
    ap.add_argument('--base-url', default='https://YOUR_USERNAME.github.io/iterations')
    ap.add_argument('--output', default='project_output')
    args = ap.parse_args()

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f'reading {args.source_csv}…')
    pixels = load_pixels(args.source_csv)
    w, h = get_dims(pixels)
    print(f'  {len(pixels):,} pixels, image {w}×{h}')

    print('shuffling pixels (deterministic)…')
    shuffled = shuffle_pixels(pixels, RANDOM_SEED)

    print(f'writing {NUM_ITERATIONS} cumulative CSVs to {out_dir}/data/…')
    write_iteration_csvs(shuffled, NUM_ITERATIONS, out_dir)

    print(f'writing xlsx with {NUM_ITERATIONS} delta tabs…')
    write_delta_xlsx(shuffled, NUM_ITERATIONS, out_dir)

    print(f'writing {NUM_ITERATIONS} HTML pages…')
    write_html_pages(shuffled, NUM_ITERATIONS, w, h, out_dir)

    print('writing index.html…')
    write_index(NUM_ITERATIONS, out_dir)

    print(f'writing {NUM_ITERATIONS} QR codes…')
    write_qr_codes(NUM_ITERATIONS, args.base_url, out_dir)

    print('writing README.md…')
    with open(out_dir / 'README.md', 'w') as f:
        f.write(README.format(base_url=args.base_url.rstrip('/')))

    print(f'\nDone. Project written to: {out_dir.resolve()}')


if __name__ == '__main__':
    main()
