/** @odoo-module */
import {_t} from "@web/core/l10n/translation";

/** Teintes des couvertures de remplacement (album sans image), choisies par série. */
const PALETTE = ["#1d2a5b", "#a9843e", "#b5694a", "#244a73", "#6b3b55", "#2f4f3a", "#7a3f2a", "#3d5a80"];

export function serieColor(name) {
    let hash = 0;
    for (const ch of String(name || "")) {
        hash = (hash * 31 + ch.charCodeAt(0)) % 9973;
    }
    return PALETTE[hash % PALETTE.length];
}

export function readingLabel(reading) {
    return {non_lu: _t("Unread"), en_cours: _t("Reading"), lu: _t("Read")}[reading] || "";
}

export const NEXT_READING = {non_lu: "en_cours", en_cours: "lu", lu: "non_lu"};
