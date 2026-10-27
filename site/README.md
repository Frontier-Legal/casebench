# casebench.dev

The Casebench website and documentation: Astro with Starlight, deployed as a static site.

```sh
cd site
npm ci
npm run dev       # http://localhost:4321
npm test          # unit tests for src/lib, with Node's test runner
npm run check     # types
npm run build     # the static site in dist/; fails on a broken link or anchor
```

Node 22.18 or later.

## Where things are

| Path | Holds |
| --- | --- |
| `src/content/docs/` | Every page, in Markdown or MDX. The folder is the URL. |
| `src/content/docs/developers/`, `lawyers/` | The two audiences, each split into `tutorials/`, `guides/`, `concepts/` and `reference/`. The folder sets the label above each page's title (`src/lib/taxonomy.ts`). |
| `src/components/` | The landing page, the header and page-title overrides, screenshots and the format tables. |
| `src/styles/tokens.css` | Colours, type and shape. Every other style reads these. |
| `src/assets/screens/` | Workbench screenshots, used with `<Screenshot name="..." />`. |
| `src/content/i18n/en.json` | The site's own interface strings. |
| `openapi/capture-server.yaml` | The capture server's API, rendered under `/developers/reference/capture-api/`. |
| `scripts/cli_reference.py` | Writes the command-line reference from the commands' own help. |

## Pages generated from the code

- **Command line.** Run `uv run python site/scripts/cli_reference.py` from the repository root after changing a command's help. `tests/site/test_reference_pages.py` fails when the page is out of date.
- **File formats.** The field tables read the JSON Schemas in `casebench/formats/schemas/` at build time.
- **Capture server API.** The same test checks that `openapi/capture-server.yaml` lists the routes the server serves.
- **Changelog.** The page renders the repository's `CHANGELOG.md`, which the release tooling writes.

## Writing

- Each page does one job: a tutorial, a how-to guide, a concept or a reference. Put it in the matching folder.
- Every page has a `description` of at least 40 characters; the build refuses a page without one.
- Lawyer pages describe the workbench only, with screenshots. Commands belong in the developer pages.
- Plain words, sentence-case headings, no em dashes.

## Screenshots

Screenshots are taken from a running workbench at 1280 pixels wide and a device scale of 2, on demo data about the fictional jurisdiction of Examplia. Replace a file in `src/assets/screens/` under the same name to update every page that shows it.

## Versions

The site documents the version on `main`; the header shows it, read from `pyproject.toml`. When a release needs its docs kept after the next one ships, deploy the site as built at that release's tag at an address of its own, such as `https://0-5.casebench.dev/`, and list it in `versions.json`, newest first:

```json
[{ "label": "0.5", "url": "https://0-5.casebench.dev/" }]
```

The header then becomes a menu that links to each archived version. Each one keeps its own pages and links exactly as they were at its tag. `src/lib/versions.test.ts` checks the file.

## Languages

English is the root locale. To add one, add it under `locales` in `astro.config.mjs`, translate `src/content/i18n/en.json` into a file named after it, and add pages under `src/content/docs/<locale>/`. A page not yet translated falls back to English with a notice.

## Deployment

`vercel.json` builds with `npm ci` and `npm run build` and serves `dist/`, with long caching for hashed assets. Set the Vercel project's root directory to `site`.
