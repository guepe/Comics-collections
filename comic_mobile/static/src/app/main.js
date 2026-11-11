/** @odoo-module */
import {whenReady} from "@odoo/owl";
import {mountComponent} from "@web/env";
import {ComicMobileApp} from "./app";

whenReady(async () => {
    await mountComponent(ComicMobileApp, document.body);
    // App démarrée : on retire un éventuel message d'erreur affiché pendant le démarrage
    window.__comicMobileStarted = true;
    const box = document.getElementById("o_cm_boot_error");
    if (box) {
        console.warn("comic_mobile: startup message removed after start:", box.textContent);
        box.remove();
    }
});
