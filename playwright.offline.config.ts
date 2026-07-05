// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Records a real video of the lsat-mobile PWA doing offline review + reconnect sync
// against the real standalone lsat/server (the Android backend). Run:
//   BUILD_ROOT=... just rebuild-web            # bake the offline client into the PWA
//   out/node_modules/.bin/playwright test --config playwright.offline.config.ts
// The .webm recording lands in out/e2e-offline/.

import { defineConfig, devices } from "@playwright/test";

const PORT = process.env.ANKI_API_PORT ?? "40123";
const PYENV_PYTHON = process.platform === "win32"
    ? "out\\pyenv\\Scripts\\python.exe"
    : "out/pyenv/bin/python";

export default defineConfig({
    // Its own dir so the default e2e config (ts/tests/e2e, Anki-launcher webServer)
    // never picks it up -- this test needs the tokenless lsat/server webServer below.
    testDir: "./ts/tests/e2e-offline",
    outputDir: "./out/e2e-offline",
    fullyParallel: false,
    workers: 1,
    retries: 0,
    reporter: "list",
    use: {
        ...devices["Pixel 7"], // phone form factor so the recording reads as a phone
        baseURL: `http://127.0.0.1:${PORT}`,
        video: "on", // <-- the recording
        trace: "on",
    },
    webServer: {
        command: `${PYENV_PYTHON} qt/tests/launch_lsat_server_for_e2e.py`,
        url: `http://127.0.0.1:${PORT}/healthz`,
        timeout: 120_000,
        reuseExistingServer: false,
        stdout: "pipe",
        stderr: "pipe",
        env: {
            ANKI_API_PORT: String(PORT),
            BUILD_ROOT: process.env.BUILD_ROOT ?? "",
        },
    },
});
