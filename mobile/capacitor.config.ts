import type { CapacitorConfig } from "@capacitor/cli";

// The Android app is a thin WebView wrapper: it loads the lsat-mobile PWA
// directly from the hosted backend (lsat/server), which serves both the PWA and
// the /_anki/lsat* API from one origin (so the existing client works unchanged,
// no CORS). Point it at your server with the LSAT_SERVER_URL env var at build
// time, e.g.:
//
//   # Android emulator, server on the host machine (default below):
//   LSAT_SERVER_URL="http://10.0.2.2:8000/lsat-mobile" npx cap sync android
//   # Real device on your Wi-Fi (server without a token):
//   LSAT_SERVER_URL="http://192.168.1.42:8000/lsat-mobile" npx cap sync android
//   # Hosted server with a pairing token (recommended; HTTPS):
//   LSAT_SERVER_URL="https://lsat.example.com/lsat-mobile#token=YOUR_TOKEN" npx cap sync android
//
// The #token=... fragment is read by the PWA (ts/lib/lsat/client.ts initToken),
// stored, and stripped from the address bar on first load.
const SERVER_URL =
    process.env.LSAT_SERVER_URL ?? "http://10.0.2.2:8000/lsat-mobile";

const config: CapacitorConfig = {
    appId: "com.lsat.prep",
    appName: "LSAT Prep",
    // Local shell used only if SERVER_URL is removed; with server.url set the
    // WebView loads the remote PWA. Kept so `cap sync` has a webDir.
    webDir: "www",
    server: {
        url: SERVER_URL,
        // Android blocks cleartext by default; allow it only for http:// (LAN /
        // emulator). A hosted https:// server needs no cleartext.
        cleartext: SERVER_URL.startsWith("http://"),
        allowNavigation: [new URL(SERVER_URL).host],
    },
    android: {
        backgroundColor: "#f4f6f9",
    },
};

export default config;
