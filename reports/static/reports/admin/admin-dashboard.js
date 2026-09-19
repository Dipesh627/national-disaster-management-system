document.addEventListener("DOMContentLoaded", function () {
    const dashboard = document.querySelector(".ndms-dashboard");
    if (!dashboard) return;

    const statusContent = dashboard.querySelector(".status-content");
    const statusList = dashboard.querySelector(".status-list");
    const ring = dashboard.querySelector(".status-ring");

    if (!statusContent || !statusList) return;

    const total = Number(ring?.dataset.total || 0);
    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    statusList.querySelectorAll(".status-bar").forEach(function (bar) {
        const count = Number(bar.dataset.count || 0);
        const percentage = total > 0 ? Math.min((count / total) * 100, 100) : 0;

        if (prefersReducedMotion) {
            bar.style.width = percentage + "%";
            return;
        }

        requestAnimationFrame(function () {
            bar.style.width = percentage + "%";
        });
    });

    if (ring) {
        const verified = Number(
            statusList.querySelector(".status-bar-verified")?.dataset.count || 0
        );
        const percentage = total > 0 ? Math.min((verified / total) * 100, 100) : 0;

        if (prefersReducedMotion) {
            ring.style.setProperty("--status-pct", percentage + "%");
        } else {
            requestAnimationFrame(function () {
                ring.style.setProperty("--status-pct", percentage + "%");
            });
        }
    }
});
