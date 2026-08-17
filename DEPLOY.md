# Deploying to uniexams.co.uk

`index.html` is a self-contained static page. On every push to `main` that
changes `index.html`, `.github/workflows/deploy.yml` uploads it via FTPS to
Porkbun hosting's `public_html`, where it's served as the live site.

## One-time setup

1. In your Porkbun account, open the hosting panel for `uniexams.co.uk` and
   find (or create, via cPanel → FTP Accounts) an FTP account with access to
   `public_html`.
2. In this repo on GitHub: **Settings → Secrets and variables → Actions →
   New repository secret**, add:
   - `PORKBUN_FTP_SERVER` — the FTP host (e.g. `ftp.uniexams.co.uk` or the
     hostname/IP Porkbun gives you)
   - `PORKBUN_FTP_USERNAME`
   - `PORKBUN_FTP_PASSWORD`
   - `PORKBUN_FTP_DIR` — the remote upload path, normally `public_html/`
3. Push a change to `index.html` on `main` (or re-run the workflow manually
   from the Actions tab) to trigger the first deploy.

## DNS

Domain and hosting both being on Porkbun usually means DNS is already
pointed at the hosting automatically. If `uniexams.co.uk` doesn't resolve to
the site, check the DNS panel for the domain and make sure the `A`/`ALIAS`
records point at the hosting (Porkbun's hosting UI typically sets this up
for you when hosting is provisioned).
