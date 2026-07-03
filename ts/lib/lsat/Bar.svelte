<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
-->
<script lang="ts">
    import type { Status } from "./types";
    import { clamp01, statusColor } from "./util";

    export let value = 0; // 0-1
    export let status: Status = "neutral";
    export let height = 10;

    $: width = clamp01(value) * 100;
    $: c = statusColor(status);
</script>

<div class="lsat-bar" style="--h:{height}px;--c:{c}">
    <div class="fill" style="width:{width}%"></div>
</div>

<style lang="scss">
    .lsat-bar {
        height: var(--h);
        border-radius: var(--lsat-radius-pill);
        background: var(--lsat-inset);
        border: 1px solid var(--lsat-border-subtle);
        overflow: hidden;
    }
    .fill {
        height: 100%;
        /* a subtle gradient from the status colour toward the violet secondary,
         * with a faint top sheen -- reads as one design system across panels */
        background:
            linear-gradient(
                180deg,
                rgba(255, 255, 255, 0.22) 0%,
                rgba(255, 255, 255, 0) 55%
            ),
            linear-gradient(
                90deg,
                var(--c) 0%,
                color-mix(in srgb, var(--c) 62%, var(--lsat-accent-2)) 100%
            );
        border-radius: inherit;
        transition: width var(--lsat-transition) var(--lsat-ease);
    }
</style>
