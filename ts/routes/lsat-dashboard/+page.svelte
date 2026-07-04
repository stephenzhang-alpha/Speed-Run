<!--
Copyright: Ankitects Pty Ltd and contributors
License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

The dashboard route (desktop home screen). The proof-header hero now lives inside
the shared DashboardView so it is identical here and in the mobile Progress tab
(Android). This route just provides the graph-paper canvas + width.
-->
<script lang="ts">
    import "$lib/lsat/theme.scss";

    import DashboardView from "$lib/lsat/DashboardView.svelte";

    import type { PageData } from "./$types";

    export let data: PageData;
</script>

<div class="dash">
    <DashboardView dashboard={data.dashboard} />
</div>

<style lang="scss">
    .dash {
        max-width: var(--lsat-maxw);
        margin: 0 auto;
        padding: 1.25rem 1.75rem 3.5rem;
        color: var(--lsat-fg);
        /* soft brand-aura page background (replaces the old graph-paper grid) */
        background: var(--lsat-bg);
        min-height: 100vh;
        font-size: 14px;
        line-height: 1.45;
    }
</style>
