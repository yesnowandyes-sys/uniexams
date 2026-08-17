# Deploying to uniexams.co.uk

`index.html` is a self-contained static page, published to
**uniexams.co.uk** via **GitHub Pages**. `.github/workflows/pages.yml`
publishes only `index.html` (not `app.py`, `scripts/`, etc.) on every push to
`main` that changes it.

## One-time setup

### 1. Turn on Pages for this repo

In this repo on GitHub: **Settings → Pages**. Under "Build and deployment",
set **Source** to **GitHub Actions**. That's it — no branch/folder picker
needed, the workflow handles publishing.

### 2. Point DNS at GitHub Pages

In Porkbun, on the **DNS** panel for `uniexams.co.uk` (the "DNS" link next to
the domain in Domain Management — not the hosting panel), add:

| Type  | Host  | Answer                |
|-------|-------|------------------------|
| A     | (blank / @) | `185.199.108.153` |
| A     | (blank / @) | `185.199.109.153` |
| A     | (blank / @) | `185.199.110.153` |
| A     | (blank / @) | `185.199.111.153` |
| CNAME | www   | `yesnowandyes-sys.github.io` |

Remove/replace any existing A or CNAME records at the apex (`@`) or `www`
that point elsewhere (e.g. at the old WordPress hosting), so they don't
conflict.

### 3. Set the custom domain in GitHub

Still in **Settings → Pages**, under "Custom domain" enter
`uniexams.co.uk` and save. GitHub will check the DNS records above (can take
up to a few hours to propagate) and then offer an **Enforce HTTPS**
checkbox — turn that on once it's available.

### 4. Trigger the first deploy

Push a change to `index.html` on `main`, or go to the **Actions** tab →
"Deploy to GitHub Pages" → **Run workflow**.

## Notes

- The Porkbun WordPress hosting product is no longer in the request path for
  this domain once DNS points at GitHub Pages above. It's safe to leave
  idle or downgrade/cancel separately — not required for this to work.
- `app.py` / `auto-pull.sh` still run the local preview server on port 5051,
  unrelated to the live site.
