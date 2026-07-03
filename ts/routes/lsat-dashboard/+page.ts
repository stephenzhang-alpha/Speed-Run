// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import type { PageLoad } from "./$types";

// The dashboard data comes from a custom mediasrv endpoint (a Python handler
// that runs the local LSAT models), not a generated protobuf RPC, so we POST to
// it directly. The webview injects the Bearer token, and the "application/binary"
// content-type satisfies mediasrv's same-origin check.
export const load = (async ({ fetch }) => {
    const resp = await fetch("/_anki/lsatDashboardData", {
        method: "POST",
        headers: { "Content-Type": "application/binary" },
        body: new Uint8Array(),
    });
    if (!resp.ok) {
        throw new Error(`${resp.status}: ${await resp.text()}`);
    }
    const dashboard = await resp.json();
    return { dashboard };
}) satisfies PageLoad;
