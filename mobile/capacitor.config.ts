import type { CapacitorConfig } from "@capacitor/cli";

// The Android app supports TWO deployment modes. Offline review + reconnect sync
// (the durable answer queue + item prefetch in ts/lib/lsat/client.ts) works in BOTH;
// they differ only in where the app SHELL loads from.
//
// 1) REMOTE (default) — a thin WebView that loads the lsat-mobile PWA from the hosted
//    backend (lsat/server), which serves the PWA and the /_anki/lsat* API from one
//    origin (so client.ts's relative requests work with no CORS). Simplest, but the
//    SHELL needs the network to load the first time each session:
//        LSAT_SERVER_URL="http://10.0.2.2:8000/lsat-mobile" npx cap sync android      # emulator
//        LSAT_SERVER_URL="http://192.168.1.42:8000/lsat-mobile" npx cap sync android  # LAN device
//        LSAT_SERVER_URL="https://lsat.example.com/lsat-mobile#token=YOUR_TOKEN" npx cap sync android
//
// 2) LOCAL_BUNDLE (recommended for the phone requirement) — the built PWA is bundled
//    INTO the app (webDir), so the shell loads with NO network at all; only data +
//    the answer-sync queue talk to the server, at the absolute origin baked into
//    LSAT_API_BASE (client.ts apiBase()). This is the mode where a learner can open
//    the app on a plane, review from the prefetch cache, and have answers sync on
//    reconnect. Build it with:
//        ./ninja sveltekit                                  # build the PWA
//        cp -r "$BUILD_ROOT"/sveltekit/* mobile/www/        # bundle the shell locally
//        LSAT_LOCAL_BUNDLE=1 \
//        LSAT_API_BASE="https://lsat.example.com" \
//        LSAT_PAIR_URL="https://lsat.example.com/lsat-mobile#api=https://lsat.example.com&token=YOUR_TOKEN" \
//          npx cap sync android
//    Pair once by opening LSAT_PAIR_URL (initToken persists the #api= origin + #token=),
//    after which the locally-bundled shell reaches the server directly.
//
// The #token=... / #api=... fragments are read by ts/lib/lsat/client.ts (initToken),
// stored in localStorage, and stripped from the address bar on first load.

const LOCAL_BUNDLE = process.env.LSAT_LOCAL_BUNDLE === "1";
const SERVER_URL = process.env.LSAT_SERVER_URL ?? "http://10.0.2.2:8000/lsat-mobile";
// In LOCAL_BUNDLE mode the shell loads locally but still POSTs to this absolute API
// origin (client.ts apiBase()); Android blocks cleartext http by default, so it must
// be allow-listed for an http base (emulator 10.0.2.2 / LAN). https needs nothing.
const API_BASE = process.env.LSAT_API_BASE ?? "";

const config: CapacitorConfig = {
    appId: "com.lsat.prep",
    appName: "LSAT Prep",
    // In LOCAL_BUNDLE mode the app serves this directory (the bundled PWA) itself, so
    // the shell is available offline. In REMOTE mode it is only the fallback shell.
    webDir: "www",
    // REMOTE mode points the WebView at the hosted PWA; LOCAL_BUNDLE mode omits
    // server.url entirely so the bundled webDir loads locally (offline-capable shell).
    ...(LOCAL_BUNDLE
        // Local shell: no server.url (it loads offline), but allow cleartext to the
        // http API origin so submits/sync reach the emulator/LAN server.
        ? API_BASE.startsWith("http://")
            ? { server: { cleartext: true, allowNavigation: [new URL(API_BASE).host] } }
            : {}
        : {
            server: {
                // Android blocks cleartext by default; allow it only for http://
                // (LAN / emulator). A hosted https:// server needs no cleartext.
                url: SERVER_URL,
                cleartext: SERVER_URL.startsWith("http://"),
                allowNavigation: [new URL(SERVER_URL).host],
            },
        }),
    android: {
        backgroundColor: "#f4f6f9",
    },
};

export default config;
