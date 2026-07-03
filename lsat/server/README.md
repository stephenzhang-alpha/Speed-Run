# LSAT standalone backend

Serves the `lsat-mobile` PWA and the `/_anki/lsat*` API from one origin, running
the Python `lsat/` layer against a directly-opened Anki collection (no Qt). The
Android app ([../../mobile/](../../mobile/)) is a Capacitor WebView that loads
`<server>/lsat-mobile` from here.

## Endpoints

- `GET  /lsat-mobile` (+ `/_app/*`) - the built PWA (SPA).
- `GET  /healthz` - liveness check.
- `POST /_anki/lsatDashboardData` - scores + insights + coverage.
- `POST /_anki/lsatNextItem` - the next item to study.
- `POST /_anki/lsatSubmitAnswer` - grade + log an answer.
- `POST /_anki/lsatSubmitTrap` - grade a "which trap?" tap.
- `POST /_anki/lsatSubmitClassify` - grade the identification stage.

All POSTs require `Authorization: Bearer <token>` when a token is configured.
The PWA reads the token from a `#token=<token>` URL fragment (see
`ts/lib/lsat/client.ts`), so hand the phone `https://<server>/lsat-mobile#token=<token>`.

## Run from the repo (dev)

```bash
./ninja sveltekit                       # build the PWA once
LSAT_SERVER_TOKEN=changeme lsat/server/run.sh \
    --collection ~/lsat/collection.anki2 --port 8000
```

Uses the repo's `out/pyenv` Python and the local `anki` (with the points-at-stake
Rust RPC), so ZPD selection is fully active. Open
`http://<your-ip>:8000/lsat-mobile#token=changeme` on a phone on the same Wi-Fi.

## Run with Docker (hosted)

```bash
./ninja sveltekit                       # produces out/sveltekit/
docker build -f lsat/server/Dockerfile -t lsat-backend .
docker run -p 8000:8000 \
    -e LSAT_SERVER_TOKEN=changeme \
    -v "$PWD/data:/data" \
    lsat-backend
```

Seed a collection into `./data/collection.anki2` first (e.g.
`python -m lsat.seed --collection ./data/collection.anki2`).

## Production notes

- **Single worker only.** The Anki backend is not thread-safe; the server opens
  one collection and serializes requests on a lock. Do not run multiple workers
  or threads against one collection (the Docker `CMD` uses `--threads=1`).
- **HTTPS.** Android blocks cleartext HTTP by default, so a non-LAN deployment
  needs TLS. Put the container behind a reverse proxy that terminates TLS, e.g.
  Caddy:

  ```
  lsat.example.com {
      reverse_proxy localhost:8000
  }
  ```

  Then the app's server URL is `https://lsat.example.com`. (For LAN-only dev you
  can instead allow cleartext in the app via `usesCleartextTraffic`; see
  [../../mobile/README.md](../../mobile/README.md).)
- **Anki version.** `pip install anki` is the stock backend (no custom Rust RPC),
  so ZPD selection degrades to "any due item." For the full points-at-stake
  queue, build the repo wheel with `just wheels` and install that instead.
- **Single user.** One collection = one user. Multi-user accounts/auth are out of
  scope for this backend.
