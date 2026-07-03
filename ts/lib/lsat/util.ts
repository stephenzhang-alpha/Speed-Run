// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import type { Status } from "./types";

/** 0-1 fraction -> "72%" (em dash when null). */
export function pct(x: number | null | undefined): string {
    return x == null ? "\u2014" : `${Math.round(x * 100)}%`;
}

/** 0-1 fraction -> "+33%" / "-8%" (for indices that can be negative). */
export function signed(x: number | null | undefined): string {
    if (x == null) {
        return "\u2014";
    }
    const p = Math.round(x * 100);
    return `${p > 0 ? "+" : ""}${p}%`;
}

/** 0-1 accuracy delta -> "+14 pts" / "-8 pts" (a change in percentage points,
 *  not a percentage of anything; em dash when null). */
export function signedPoints(x: number | null | undefined): string {
    if (x == null) {
        return "\u2014";
    }
    const p = Math.round(x * 100);
    return `${p > 0 ? "+" : ""}${p} pts`;
}

export function pctRange(low: number | null, high: number | null): string {
    return low == null || high == null
        ? ""
        : `${Math.round(low * 100)}\u2013${Math.round(high * 100)}%`;
}

export function clamp01(x: number): number {
    return Math.max(0, Math.min(1, x));
}

export function statusColor(status: Status): string {
    switch (status) {
        case "good":
            return "var(--lsat-good)";
        case "warn":
            return "var(--lsat-warn)";
        case "bad":
            return "var(--lsat-bad)";
        default:
            return "var(--lsat-accent)";
    }
}

export function statusSoft(status: Status): string {
    switch (status) {
        case "good":
            return "var(--lsat-good-soft)";
        case "warn":
            return "var(--lsat-warn-soft)";
        case "bad":
            return "var(--lsat-bad-soft)";
        default:
            return "var(--lsat-accent-soft)";
    }
}

/** Map a 0-1 score to a traffic-light status (higher is better). */
export function scoreStatus(x: number | null | undefined, good = 0.75, warn = 0.5): Status {
    if (x == null) {
        return "neutral";
    }
    if (x >= good) {
        return "good";
    }
    if (x >= warn) {
        return "warn";
    }
    return "bad";
}

/** Humanize a taxonomy node id / trap family for display. */
export function humanize(id: string): string {
    return id
        .replace(/^(lsat::|skill\.|lr\.|rc\.|struct\.)/, "")
        .replace(/[_.]/g, " ")
        .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function msToSeconds(ms: number | null | undefined): string {
    return ms == null ? "\u2014" : `${(ms / 1000).toFixed(ms < 10000 ? 1 : 0)}s`;
}
