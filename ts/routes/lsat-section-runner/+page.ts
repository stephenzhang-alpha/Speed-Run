// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { initToken } from "$lib/lsat/client";

import type { PageLoad } from "./$types";

export const ssr = false;
export const prerender = false;

// The timed section runs entirely in the browser (a countdown, a per-question
// trajectory) and fetches its own items on mount, so there is no server load
// here -- we only capture the pairing token (in case the route is opened
// directly rather than via a client-side navigation from the mobile shell).
export const load = (async () => {
    initToken();
    return {};
}) satisfies PageLoad;
