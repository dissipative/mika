# Mika's care guide

A short, public, mobile-first guide for people who look after Mika, a family dog.
The guide is in four languages: English, Spanish (Spain), Valencian (AVL norms) and Russian.
It is a static site for GitHub Pages. It has no backend, no analytics and no external requests.

Planned address: <https://dissipative.github.io/mika/>
(it is live only after the first successful deploy, see [Publish](#publish-on-github-pages)).

## Language URLs

| URL | Page |
|---|---|
| `…/mika/` | English. A small script opens the saved language or the browser language. |
| `…/mika/en/` | English |
| `…/mika/es/` | Español |
| `…/mika/val/` | Valencià |
| `…/mika/ru/` | Русский |

Share a language URL to open that language directly. The switcher saves the last choice in
`localStorage` (key `mika-lang`). Only the root page reads it. Language pages never redirect.

## Project structure

| Path | Content |
|---|---|
| `content/guide.toml` | All page text, with the four languages side by side. Edit text here only. |
| `src/template.html` | Page structure. `{{key}}` is text from `guide.toml`, `{{@name}}` is a build value. |
| `src/styles.css` | Screen styles (mobile first, dark mode, reduced motion) and print styles. |
| `src/site.js` | Small enhancements: language memory, print button, print expansion. |
| `src/favicon.svg` | Icon: a white dog face with Mika's dark eye patch. |
| `assets/img/` | Optimised photos (AVIF + WebP, no metadata) and `og.jpg` for link previews. |
| `scripts/optimise-photos.sh` | Makes the files in `assets/img/` from the original photos. |
| `build.py` | Builds `_site/` and runs all checks. Python standard library only. |
| `.github/workflows/pages.yml` | Builds and deploys to GitHub Pages on each push to `main`. |

## Requirements

- Python 3.11 or later (for `tomllib`).
- ImageMagick 7 with AVIF and WebP support. You need it only to update photos.

## Preview locally

Build the site and serve it under the `/mika/` subpath, as on GitHub Pages:

```bash
python3 build.py --serve
```

Open <http://localhost:8000/mika/>. To use a different port or subpath, add options:

```bash
python3 build.py --serve 9000 --prefix /other-name/
```

## Build and checks

```bash
python3 build.py
```

The build writes `_site/` and stops with an error if one of these checks fails:

1. Each text entry has all four languages, and no entry is empty.
2. No text contains an e-mail address, a phone-like number, a URL or a placeholder such as `TODO`.
3. Bold markers (`**`) are in pairs.
4. Each template placeholder has a text entry.
5. The HTML tags are balanced, IDs are unique and each image has `alt` text.
6. Each local link, image and `srcset` entry resolves to a file inside `_site/`.
7. No URL starts with `/`. Root-absolute URLs break under a repository subpath.

The build also prints the visible word count for each language. The target is roughly
250–400 words. Spanish and Valencian are about 8 % longer than English for the same meaning.

## Edit text and translations

1. Open `content/guide.toml`.
2. Find the entry, for example `[cautions.dogs]`.
3. Change all four languages in the same edit. Keep the practical meaning identical.
4. Use `**text**` for bold. Do not use HTML.
5. Run `python3 build.py`.
6. Change `[ui.updated]` to the current month.

Rules for the content:

- Write as the family ("we"). Do not add facts that the family did not give. Do not add amounts in grams or cups: the scoop volume is not known.
- Keep the four cautions in the "Please remember" card. Keep the on-lead greeting and slipper warnings visible, not only in an accordion.
- Valencian follows the AVL norms. Keep the Valencian forms, for example `esta`, `ací`, `seua`, `protegix`, `siga`, `conéixer`, `gitar-se`, `arrere`, `roig`.
- Spanish uses Spain usage, for example `pienso`, `grifo`, `zapatilla`.

To add a new text block, add an entry in `guide.toml` and a placeholder in `src/template.html`.
The build prints a warning for an entry that the template does not use.

## Update photos

1. Put the original photos in the repository root, or in another folder.
2. Edit the `PHOTOS` list in `scripts/optimise-photos.sh`: file name, crop and widths.
3. Run the script. If the originals are in another folder, give the folder as the argument:

   ```bash
   scripts/optimise-photos.sh ~/Pictures/mika
   ```

4. Look at the new crops in `assets/img/`. Then run `python3 build.py`.
5. If you change a photo shape, change its `width` and `height` in `src/template.html`.

The script removes all metadata, including GPS location. Git ignores the original photos
(`*.jpg`, `*.jpeg`, `*.heic` in the root). Do not commit originals: their EXIF data contains the location.

The page uses these four originals:

| Output | Original | Use |
|---|---|---|
| `hero-*` | `IMG_4243.jpeg` | Main portrait |
| `grass-*` | `IMG_4854.jpeg` | Walks and other dogs |
| `beach-*` | `IMG_4945.jpeg` | Water on walks |
| `home-*` | `dclassic 2026-03-08 122005AB1035BD67CA.jpg` | At home |

`IMG_8947.jpeg` is not used. It shows Mika on a human bed, and the guide says that she has not
normally done that for over a year.

## Publish on GitHub Pages

The workflow `.github/workflows/pages.yml` builds the site and deploys `_site/`.
Do these steps one time:

1. Push the `main` branch to `github.com/dissipative/mika`.
2. On GitHub, open **Settings → Pages**.
3. Under **Build and deployment → Source**, select **GitHub Actions**.
4. Open **Actions**, select **Deploy to GitHub Pages**, then select **Run workflow**. Or push a new commit.
5. When the run is green, open <https://dissipative.github.io/mika/>.

After that, each push to `main` deploys the site again.

If the repository name or the domain changes, update `url` under `[site]` in `content/guide.toml`.
Only link previews (`og:image`, `og:url`) use it. All other URLs are relative.

## Privacy

- This page is public. Do not add an address, phone numbers, e-mail addresses, key or door codes,
  veterinarian details or other private data.
- Give private details (contact numbers, address, veterinarian, keys, emergency plan) to the sitter
  directly, for example in a private message. Do not put them in this repository.
- The page has `<meta name="robots" content="noindex">`, so search engines do not list it.
  Anyone with the link can still open it. To allow indexing, remove that line from `src/template.html`.
- The site loads no fonts, scripts or trackers from other servers.
- The published photos have no metadata. The originals stay on your computer only.

## Accessibility and print

- Semantic landmarks, a skip link, a labelled language switcher with `aria-current`, `lang` on
  each page and on each language link, and visible focus outlines.
- Text and accent colours meet WCAG AA contrast in light and dark mode.
- With `prefers-reduced-motion`, the page has no transitions and no tilted photo.
- Print or "Save as PDF" from the browser, or use the button at the bottom of the page.
  The print layout hides the controls and the section photos, opens the accordions and shows the
  page address. In Chrome, each language prints on two Letter pages.
- Without JavaScript, the page still works. Only the print button, the language memory and the
  root redirect need JavaScript.
