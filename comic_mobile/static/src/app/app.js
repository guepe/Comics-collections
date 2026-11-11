/** @odoo-module */
import {Component, useState} from "@odoo/owl";
import {MainComponentsContainer} from "@web/core/main_components_container";
import {CollectionScreen} from "./screens/collection";
import {ScanScreen} from "./screens/scan";
import {SerieScreen} from "./screens/serie";
import {WishlistScreen} from "./screens/wishlist";
import {ComicTabBar} from "./tabbar";

/**
 * App mobile (PWA) : quatre écrans — collection, scan ISBN, série, wishlist.
 * Navigation interne (pas de routeur) : l'écran courant et l'écran de retour.
 */
export class ComicMobileApp extends Component {
    static template = "comic_mobile.App";
    static components = {MainComponentsContainer, CollectionScreen, ScanScreen, SerieScreen, WishlistScreen, ComicTabBar};
    static props = {};

    setup() {
        this.state = useState({screen: "collection", tab: "collection", serieId: false, back: "collection", stamp: 0});
    }

    selectTab(screen) {
        this.state.back = this.state.tab;
        this.state.screen = screen;
        if (screen !== "scan") {
            this.state.tab = screen;
        }
        this.state.stamp++;
    }

    openSerie(serieId) {
        this.state.back = this.state.screen;
        this.state.serieId = serieId;
        this.state.screen = "serie";
    }

    goBack() {
        this.state.screen = this.state.back === "serie" || this.state.back === "scan" ? this.state.tab : this.state.back;
        this.state.stamp++;
    }
}
