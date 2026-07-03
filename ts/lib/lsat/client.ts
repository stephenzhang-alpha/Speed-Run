// Copyright: Ankitects Pty Ltd and contributors
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

// HTTP client for the LSAT mobile PWA. The desktop reviewer captures answers
// through the Qt-only `pycmd` bridge; on a phone there is no pycmd, so the PWA
// talks to the same mediasrv endpoints over HTTP. Requests use the
// "application/binary" content-type mediasrv requires, and carry a pairing
// token (handed to the phone via the desktop's "Study on your phone" dialog,
// in the URL hash) as the Bearer credential.

import type {
    AnswerResult,
    AssumptionDrill,
    AssumptionResult,
    ClassifyResult,
    ConditionalDrillData,
    ConditionalResult,
    Dashboard,
    QuantifierNegationDrill,
    QuantifierNegationResult,
    QuantifierValidityDrill,
    QuantifierValidityResult,
    QuantifierVerdict,
    ChainDrill,
    ChainResult,
    SectionAttemptResult,
    SectionItems,
    SectionQuestionAttempt,
    EvilTwinDrill,
    EvilTwinResult,
    OracleTheater,
    StemPolarityDrill,
    StemPolarityResult,
    StudyItemData,
    TrapResult,
    WorkedExampleDrill,
    WorkedStepResult,
} from "./types";

const TOKEN_KEY = "lsat-pair-token";

/** Capture a `#token=...` (or `?token=...`) pairing token into localStorage on
 * first load, then strip it from the visible URL. Returns the active token. */
export function initToken(): string {
    if (typeof window === "undefined") {
        return "";
    }
    const fromHash = new URLSearchParams(window.location.hash.replace(/^#/, ""));
    const fromQuery = new URLSearchParams(window.location.search);
    const incoming = fromHash.get("token") ?? fromQuery.get("token");
    if (incoming) {
        try {
            window.localStorage.setItem(TOKEN_KEY, incoming);
        } catch {
            /* private mode: fall through to in-memory use */
        }
        // Remove the secret from the address bar / history.
        history.replaceState(null, "", window.location.pathname);
        return incoming;
    }
    try {
        return window.localStorage.getItem(TOKEN_KEY) ?? "";
    } catch {
        return "";
    }
}

function token(): string {
    try {
        return window.localStorage.getItem(TOKEN_KEY) ?? "";
    } catch {
        return "";
    }
}

async function post<T>(path: string, payload: unknown = {}): Promise<T> {
    const headers: Record<string, string> = { "Content-Type": "application/binary" };
    const tok = token();
    if (tok) {
        headers["Authorization"] = `Bearer ${tok}`;
    }
    const resp = await fetch(`/_anki/${path}`, {
        method: "POST",
        headers,
        body: new TextEncoder().encode(JSON.stringify(payload)),
    });
    if (!resp.ok) {
        throw new Error(`${resp.status}: ${await resp.text()}`);
    }
    return (await resp.json()) as T;
}

export function getDashboard(): Promise<Dashboard> {
    return post<Dashboard>("lsatDashboardData");
}

export function nextItem(): Promise<StudyItemData> {
    return post<StudyItemData>("lsatNextItem");
}

export function submitAnswer(
    itemId: string,
    chosen: string,
    confidence: string,
    responseMs: number,
    phase = "timed",
    identified = "",
): Promise<AnswerResult> {
    return post<AnswerResult>("lsatSubmitAnswer", {
        item_id: itemId,
        chosen,
        confidence,
        response_ms: Math.max(0, Math.round(responseMs)),
        phase,
        identified,
    });
}

export function submitClassify(itemId: string, named: string): Promise<ClassifyResult> {
    return post<ClassifyResult>("lsatSubmitClassify", { item_id: itemId, named });
}

// Timed Section Runner (r4 #17): POST the whole per-question trajectory (raw
// first/final choices, never correctness) and get back the refreshed ledger. The
// server grades and persists it -- correctness never crosses the wire mid-section.
export function submitSectionAttempt(
    trajectory: SectionQuestionAttempt[],
): Promise<SectionAttemptResult> {
    return post<SectionAttemptResult>("lsatSubmitSectionAttempt", { trajectory });
}

export function chainDrill(): Promise<ChainDrill> {
    return post<ChainDrill>("lsatChainDrill");
}

export function submitChain(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<ChainResult> {
    return post<ChainResult>("lsatSubmitChain", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

// Oracle-Verified Faded Worked Example (research feature #1): fetch a partially
// worked chain derivation whose final step is blanked, then submit the chosen
// move. Every step is oracle-verified server-side, so a hallucinated step is
// never served; the correct move is withheld until submit.
export function workedExampleDrill(): Promise<WorkedExampleDrill> {
    return post<WorkedExampleDrill>("lsatWorkedExampleDrill");
}

export function submitWorkedStep(
    itemId: string,
    moveId: string,
    responseMs: number,
): Promise<WorkedStepResult> {
    return post<WorkedStepResult>("lsatSubmitWorkedStep", {
        item_id: itemId,
        move_id: moveId,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

// Oracle-proven "Skill or Luck?" evil twin: a minimally-edited variant whose
// answer flips. The oracle proves every twin server-side; grading re-derives the
// verdict from the decision procedure via the stateless twin_key.
export function evilTwinDrill(): Promise<EvilTwinDrill> {
    return post<EvilTwinDrill>("lsatEvilTwinDrill");
}

export function submitEvilTwin(
    twinKey: string,
    chosen: string,
    responseMs: number,
): Promise<EvilTwinResult> {
    return post<EvilTwinResult>("lsatSubmitEvilTwin", {
        twin_key: twinKey,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

// A batch of DISTINCT items for a timed section (stem + choices, never the answer).
// next_item returns only the single top card and doesn't advance until an answer
// is logged, so a section -- which must not submit answers mid-run -- uses this.
export function sectionItems(n = 10): Promise<SectionItems> {
    return post<SectionItems>("lsatSectionItems", { n });
}

export function submitTrap(
    itemId: string,
    chosen: string,
    family: string,
): Promise<TrapResult> {
    return post<TrapResult>("lsatSubmitTrap", { item_id: itemId, chosen, family });
}

export function conditionalDrill(): Promise<ConditionalDrillData> {
    return post<ConditionalDrillData>("lsatConditionalDrill");
}

export function submitConditional(
    itemId: string,
    sufficient: string,
    necessary: string,
    responseMs: number,
): Promise<ConditionalResult> {
    return post<ConditionalResult>("lsatSubmitConditional", {
        item_id: itemId,
        sufficient,
        necessary,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function quantifierValidityDrill(): Promise<QuantifierValidityDrill> {
    return post<QuantifierValidityDrill>("lsatQuantifierValidityDrill");
}

export function submitQuantifierValidity(
    itemId: string,
    chosen: QuantifierVerdict,
    responseMs: number,
): Promise<QuantifierValidityResult> {
    return post<QuantifierValidityResult>("lsatSubmitQuantifierValidity", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function quantifierNegationDrill(): Promise<QuantifierNegationDrill> {
    return post<QuantifierNegationDrill>("lsatQuantifierNegationDrill");
}

export function submitQuantifierNegation(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<QuantifierNegationResult> {
    return post<QuantifierNegationResult>("lsatSubmitQuantifierNegation", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function stemPolarityDrill(): Promise<StemPolarityDrill> {
    return post<StemPolarityDrill>("lsatStemPolarityDrill");
}

export function submitStemPolarity(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<StemPolarityResult> {
    return post<StemPolarityResult>("lsatSubmitStemPolarity", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}

export function assumptionDrill(): Promise<AssumptionDrill> {
    return post<AssumptionDrill>("lsatAssumptionDrill");
}

// Oracle Proof Theater (marquee AI demo): fetch the recorded model drafts whose
// every step is checked LIVE by the material-entailment oracle server-side, so
// the planted hallucination is blocked with the oracle's reason and the provable
// continuation is substituted. Read-only; no submit counterpart.
export function oracleTheater(): Promise<OracleTheater> {
    return post<OracleTheater>("lsatOracleTheater");
}

export function submitAssumption(
    itemId: string,
    chosen: string,
    responseMs: number,
): Promise<AssumptionResult> {
    return post<AssumptionResult>("lsatSubmitAssumption", {
        item_id: itemId,
        chosen,
        response_ms: Math.max(0, Math.round(responseMs)),
    });
}
