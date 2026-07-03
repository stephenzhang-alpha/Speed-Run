# Copyright: Ankitects Pty Ltd and contributors
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
#
# Standalone LSAT backend image. Build the PWA first (from the repo root):
#     ./ninja sveltekit          # produces out/sveltekit/
# then build from the repo root:
#     docker build -f lsat/server/Dockerfile -t lsat-backend .
#
# NOTE on the Anki version: `pip install anki` (below) is the STOCK backend, so
# the custom points-at-stake Rust RPC is absent and ZPD item selection degrades
# gracefully to "any due item" (guarded in lsat/api.py). For the full queue,
# build the repo wheel (`just wheels`) and COPY/`pip install` it instead of the
# PyPI package.

FROM python:3.13-slim

WORKDIR /app

# anki = the pylib backend; the rest are the server's only extra deps.
RUN pip install --no-cache-dir anki flask waitress pyyaml

# The LSAT layer + its taxonomy (taxonomy.py reads lsat-taxonomy.yaml from the
# parent of the lsat/ package, i.e. /app).
COPY lsat/ /app/lsat/
COPY lsat-taxonomy.yaml /app/

# The built PWA. LSAT_WEB_ROOT points at the dir CONTAINING sveltekit/.
COPY out/sveltekit/ /app/web/sveltekit/
ENV LSAT_WEB_ROOT=/app/web

# Collection lives on a mounted volume; token supplied at run time.
ENV LSAT_COLLECTION=/data/collection.anki2
ENV LSAT_SERVER_TOKEN=""
VOLUME ["/data"]
EXPOSE 8000

# Single worker + single thread: the Anki backend is not thread-safe.
CMD ["waitress-serve", "--listen=0.0.0.0:8000", "--threads=1", "lsat.server.wsgi:app"]
