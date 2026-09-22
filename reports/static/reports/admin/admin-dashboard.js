document.addEventListener("DOMContentLoaded", function () {
    const dashboard = document.querySelector(".ndms-dashboard");
    if (!dashboard) return;

    const statusList = dashboard.querySelector(".status-list");
    if (!statusList) return;

    const bars = statusList.querySelectorAll(".status-bar");
    const total = Array.from(bars).reduce(function (sum, bar) {
        return sum + Number(bar.dataset.count || 0);
    }, 0);

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    bars.forEach(function (bar) {
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
});