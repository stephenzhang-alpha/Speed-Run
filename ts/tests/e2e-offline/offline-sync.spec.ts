// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// A real recording of offline review + reconnect sync: drives the actual lsat-mobile
// PWA (served by the real lsat/server backend) in a phone-sized Chromium, goes
// offline, answers an item (which is queued locally), reconnects, and confirms the
// queue syncs. Playwright records the whole thing to out/e2e-offline/.../video.webm.

import { expect, test } from "@playwright/test";

test("offline review is queued, then syncs on reconnect", async ({ page, context }) => {
    test.setTimeout(90_000);

    // --- 1. Load the mobile PWA online; it prefetches items + shows a study card ---
    await page.goto("/lsat-mobile");
    // The study card renders the stem / classify chips / choices once an item loads.
    await expect
        .poll(
            async () => (await page.locator(".stem, .classify-chips, .choices").count()) > 0,
            { timeout: 30_000 },
        )
        .toBe(true);
    await page.waitForTimeout(600); // let prefetch settle (client.prefetchItems)

    // --- 2. Go OFFLINE: the connectivity banner appears ---
    await context.setOffline(true);
    await expect(page.locator(".conn-banner.offline")).toBeVisible({ timeout: 10_000 });

    // --- 3. Answer an item while offline (classify if shown -> choice -> confidence) ---
    const chip = page.locator(".classify-chips .chip").first();
    if (await chip.isVisible().catch(() => false)) {
        await chip.click(); // classify is best-effort; offline it degrades to "answering"
    }
    await page.locator(".choices .choice").first().click({ timeout: 10_000 });
    await page.locator(".conf .opt").first().click({ timeout: 10_000 });

    // --- 4. The answer is SAVED OFFLINE (queued), not graded ---
    await expect(page.getByText("Saved offline")).toBeVisible({ timeout: 10_000 });
    await expect(page.locator(".conn-banner.offline")).toBeVisible();

    // --- 5. Reconnect: the durable queue actually DRAINS (real sync, not just UI) ---
    await context.setOffline(false);
    // The `.offline` banner class is bound to navigator.onLine, so it clears the
    // instant connectivity returns -- asserting only that would pass even if the flush
    // silently dropped or double-POSTed the answer. Assert the DURABLE QUEUE itself
    // emptied: it reaches 0 only when the queued answer was replayed AND acked by the
    // server (append-only event logged) -- the invariant this test exists to protect.
    await expect
        .poll(
            async () =>
                await page.evaluate(
                    () => JSON.parse(localStorage.getItem("lsat-offline-queue") || "[]").length,
                ),
            { timeout: 15_000 },
        )
        .toBe(0);
    // the whole banner (offline OR "N queued") is gone only when online && pending===0
    await expect(page.locator(".conn-banner")).toBeHidden({ timeout: 5_000 });

    // pause on the synced state so the recording ends on a clear frame
    await page.waitForTimeout(1000);
});

test("the app-shell service worker is served, registers, and controls the page", async ({ page }) => {
    test.setTimeout(60_000);

    // the backend serves a root-scoped app-shell service worker as JS
    const swResp = await page.request.get("/service-worker.js");
    expect(swResp.status()).toBe(200);
    expect(swResp.headers()["content-type"]).toContain("javascript");
    expect(swResp.headers()["service-worker-allowed"]).toBe("/");

    // load the PWA; pwa.ts registers the SW, which activates + claims the page. Once
    // it controls the page, GETs run through its cache-on-fetch handler, populating
    // the offline shell cache over normal use. (The GUARANTEED cold-offline shell is
    // the Capacitor local-bundle mode, which ships the shell inside the app.)
    await page.goto("/lsat-mobile");
    await page.waitForFunction(
        () => "serviceWorker" in navigator && navigator.serviceWorker.controller !== null,
        null,
        { timeout: 25_000 },
    );
    const scope = await page.evaluate(async () => {
        const reg = await navigator.serviceWorker.getRegistration();
        return reg?.scope ?? "";
    });
    expect(scope.endsWith("/")).toBe(true); // root scope covers /lsat-mobile
});
