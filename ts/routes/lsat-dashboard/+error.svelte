<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

Themed error boundary for the dashboard route. A failed (or malformed) dashboard
load previously fell through to the root +error.svelte, which renders a bare,
unstyled message — a dead-end in the ~900x900 desktop Practice window. This keeps
the failure on-brand and, crucially, recoverable: "Try again" re-runs load().
-->
<script lang="ts">
    import "$lib/lsat/theme.scss";

    import { invalidateAll } from "$app/navigation";
    import { page } from "$app/state";

    $: status = page.status;
    $: message = page.error?.message;
</script>

<div class="lsat-error">
    <div class="card">
        <h1>We couldn't load your dashboard</h1>
        <p class="lede">Your progress is safe — this is just a hiccup fetching it.</p>
        <button type="button" class="retry" on:click={() => invalidateAll()}>
            Try again
        </button>
        <p class="detail">
            {#if message}
                {status} — {message}
            {:else}
                Error {status}
            {/if}
        </p>
    </div>
</div>

<style lang="scss">
    .lsat-error {
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100vh;
        padding: 1.75rem;
        color: var(--lsat-fg);
        background: var(--lsat-bg);
        font-family: var(--lsat-font);
        font-size: 14px;
        line-height: 1.45;
    }

    .card {
        max-width: 26rem;
        width: 100%;
        text-align: center;
        padding: 2rem 1.75rem;
        background: var(--lsat-surface);
        border: 1px solid var(--lsat-border);
        border-radius: var(--lsat-radius);
        box-shadow: var(--lsat-shadow);
    }

    h1 {
        margin: 0 0 0.5rem;
        font-size: 1.15rem;
        font-weight: 700;
        color: var(--lsat-fg);
    }

    .lede {
        margin: 0 0 1.5rem;
        color: var(--lsat-fg-subtle);
    }

    .retry {
        appearance: none;
        border: none;
        cursor: pointer;
        font: inherit;
        font-weight: 600;
        padding: 0.6rem 1.4rem;
        border-radius: var(--lsat-radius-pill);
        color: var(--lsat-ink-on-accent);
        background: var(--lsat-accent);
        box-shadow: var(--lsat-shadow);
        transition: background var(--lsat-transition) var(--lsat-ease);

        &:hover {
            background: var(--lsat-accent-strong);
        }

        &:focus-visible {
            outline: none;
            box-shadow: var(--lsat-ring);
        }
    }

    .detail {
        margin: 1.5rem 0 0;
        font-family: var(--lsat-mono);
        font-size: 0.75rem;
        color: var(--lsat-fg-faint);
        word-break: break-word;
    }
</style>
