# aimbot backend

FastAPI service that scrapes news, weather, family notices and job listings and
renders them into emails/radio scripts.

## Scraping proxy (tinyproxy over Tailscale)

All outbound scraping requests are routed through a single proxy. This lets the
server keep a stable, residential egress IP by pointing scraping traffic at a
tinyproxy instance running on a Raspberry Pi at home, reached over Tailscale.

Every scraper builds its HTTP session through
`aimbot.scrapers.config.create_client_session()`, which attaches the configured
proxy to the `aiohttp.ClientSession`. There is no per-request wiring to
remember when adding a new scraper: use `create_client_session()` instead of
`aiohttp.ClientSession()`.

### Configuration

Set the proxy URL in the environment (or in the repo-root `.env`, which is
loaded automatically):

```dotenv
SCRAPER_PROXY_URL=http://raspberrypi.<your-tailnet>.ts.net:8888
```

`8888` is tinyproxy's default port. If `SCRAPER_PROXY_URL` is unset, the
standard `HTTPS_PROXY` / `HTTP_PROXY` variables are used as a fallback. When
none are set, requests go out directly (useful for local development).

The proxy is resolved when the session is created, so changing the env var only
requires a process restart.

### Raspberry Pi / tinyproxy

Example `/etc/tinyproxy/tinyproxy.conf`:

```conf
Port 8888
# Bind to the Tailscale interface/address (use `tailscale ip -4` to find it),
# or 0.0.0.0 if the Pi's firewall restricts access to the tailnet.
Listen 0.0.0.0

# Tailscale hands out addresses in the 100.64.0.0/10 CGNAT range.
Allow 100.64.0.0/10

# Only allow proxying to web ports.
ConnectPort 443
ConnectPort 80

# Optional: require credentials (then use
# SCRAPER_PROXY_URL=http://user:pass@host:8888).
#BasicAuth user password
```

Restart after editing: `sudo systemctl restart tinyproxy`.

Make sure the server can reach the Pi on port 8888 over Tailscale (check the
Tailscale ACLs if it cannot).

### Verifying

From the server:

```bash
curl -x http://raspberrypi.<your-tailnet>.ts.net:8888 https://ifconfig.me
```

The returned IP should be the Raspberry Pi's home connection, not the server's.
