// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Make the mobile route installable as a PWA ("Add to Home Screen"). The web
// app manifest is generated at runtime as a Blob URL so start_url/scope match
// whatever path mediasrv serves the page from (avoiding fragile static-asset
// paths under /_anki/). Icons are inline SVG data URIs, so no binary assets or
// build wiring are needed.

const ACCENT = "#2f6fed";

function iconDataUri(): string {
    const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512">
<rect width="512" height="512" rx="112" fill="${ACCENT}"/>
<text x="256" y="330" font-family="Helvetica, Arial, sans-serif" font-size="188"
 font-weight="700" fill="#ffffff" text-anchor="middle">LR</text></svg>`;
    return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function upsertLink(rel: string, href: string): void {
    let el = document.querySelector<HTMLLinkElement>(`link[rel="${rel}"]`);
    if (!el) {
        el = document.createElement("link");
        el.rel = rel;
        document.head.appendChild(el);
    }
    el.href = href;
}

function upsertMeta(name: string, content: string): void {
    let el = document.querySelector<HTMLMetaElement>(`meta[name="${name}"]`);
    if (!el) {
        el = document.createElement("meta");
        el.name = name;
        document.head.appendChild(el);
    }
    el.content = content;
}

/** Attach the manifest + iOS/Android install metadata to the document head. */
export function installPwaMeta(name = "LSAT Prep", short = "LSAT"): void {
    if (typeof document === "undefined") {
        return;
    }
    const icon = iconDataUri();
    const start = window.location.pathname + window.location.search;
    const manifest = {
        name,
        short_name: short,
        description: "Spaced LSAT practice that reads how you get questions wrong.",
        start_url: start,
        scope: "./",
        display: "standalone",
        orientation: "portrait",
        background_color: "#f4f6f9",
        theme_color: ACCENT,
        icons: [
            { src: icon, sizes: "192x192", type: "image/svg+xml", purpose: "any" },
            { src: icon, sizes: "512x512", type: "image/svg+xml", purpose: "any maskable" },
        ],
    };
    const blob = new Blob([JSON.stringify(manifest)], { type: "application/manifest+json" });
    upsertLink("manifest", URL.createObjectURL(blob));
    upsertLink("apple-touch-icon", icon);
    upsertLink("icon", icon);
    upsertMeta("theme-color", ACCENT);
    upsertMeta("apple-mobile-web-app-capable", "yes");
    upsertMeta("apple-mobile-web-app-title", short);
    upsertMeta("apple-mobile-web-app-status-bar-style", "default");
    upsertMeta("mobile-web-app-capable", "yes");
}
