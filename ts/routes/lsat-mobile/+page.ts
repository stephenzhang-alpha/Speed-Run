// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { getDashboard, initToken } from "$lib/lsat/client";
import type { Dashboard } from "$lib/lsat/types";

import type { PageLoad } from "./$types";

export const ssr = false;
export const prerender = false;

// The mobile PWA is served by the desktop app's mediasrv. On first open it
// captures the pairing token from the URL hash, then loads the dashboard for the
// Progress tab (the Study tab fetches its own items). A failure here is
// non-fatal: the page shows a "not connected" hint and the Study tab still works.
export const load = (async () => {
    initToken();
    let dashboard: Dashboard | null = null;
    let error = "";
    try {
        dashboard = await getDashboard();
    } catch (e) {
        error = String(e);
    }
    return { dashboard, error };
}) satisfies PageLoad;
