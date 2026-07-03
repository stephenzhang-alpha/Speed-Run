// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// Tracks when each Logic drill was last opened so the mobile "Drill Launcher" can
// show a small recency hint on every card. A single localStorage key holds an
// { [drillId]: epochMs } map. Every access is wrapped in try/catch, mirroring
// client.ts: private mode or wiped storage must degrade silently to "New"
// everywhere and never throw. Labels are strictly recency-worded (never accuracy
// or mastery), so nothing here fabricates a performance number.

const OPENED_KEY = "lsat-drill-opened";

const DAY_MS = 24 * 60 * 60 * 1000;
const WEEK_MS = 7 * DAY_MS;

type OpenedMap = Record<string, number>;

function read(): OpenedMap {
    try {
        const raw = window.localStorage.getItem(OPENED_KEY);
        const parsed: unknown = raw ? JSON.parse(raw) : {};
        // Coerce any non-object (incl. the literal `null`, arrays, numbers left by
        // external corruption) to {} so callers never index into null -> the file's
        // "never throw, degrade to New" contract holds for ALL stored values.
        return parsed && typeof parsed === "object" && !Array.isArray(parsed)
            ? (parsed as OpenedMap)
            : {};
    } catch {
        return {};
    }
}

/** Stamp a drill as practiced right now. Silently no-ops when storage is unavailable. */
export function markPracticed(id: string): void {
    try {
        const map = read();
        map[id] = Date.now();
        window.localStorage.setItem(OPENED_KEY, JSON.stringify(map));
    } catch {
        /* private mode / wiped storage: skip the write */
    }
}

/** Epoch ms the drill was last opened, or null if never opened / storage unavailable. */
export function lastPracticed(id: string): number | null {
    const ts = read()[id];
    return typeof ts === "number" ? ts : null;
}

export type RecencyTone = "new" | "good" | "neutral" | "warn";

/** Bucket a last-practiced timestamp into a short, recency-only hint. */
export function recency(ts: number | null): { label: string; tone: RecencyTone } {
    if (ts === null) {
        return { label: "New", tone: "new" };
    }
    const age = Date.now() - ts;
    if (age < DAY_MS) {
        return { label: "Today", tone: "good" };
    }
    if (age < WEEK_MS) {
        return { label: `${Math.floor(age / DAY_MS)}d ago`, tone: "neutral" };
    }
    return { label: "Time to refresh", tone: "warn" };
}
