/** @odoo-module */
import {Component, onWillStart, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {ComicCover} from "../cover";

const API = "comic.mobile.api";

export class WishlistScreen extends Component {
    static template = "comic_mobile.WishlistScreen";
    static components = {ComicCover};
    static props = {openSerie: Function};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({filter: "all", data: null});
        this.filters = [
            {key: "all", label: _t("All")},
            {key: "manque", label: _t("Missing")},
            {key: "upcoming", label: _t("Upcoming")},
        ];
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call(API, "mobile_get_wishlist", []);
    }

    get subtitle() {
        const d = this.state.data || {};
        return _t("%(missing)s missing volumes · %(wishes)s wishes", {missing: d.missing || 0, wishes: d.wishes || 0});
    }

    get groups() {
        const f = this.state.filter;
        const keep = (item) =>
            f === "all" || (f === "manque" && item.type === "manque" && !item.upcoming) || (f === "upcoming" && item.upcoming);
        return (this.state.data ? this.state.data.groups : [])
            .map((g) => ({...g, items: g.items.filter(keep)}))
            .filter((g) => g.items.length);
    }

    tag(item) {
        if (item.upcoming) {
            return {label: _t("Upcoming"), css: "upcoming"};
        }
        return item.type === "souhait" ? {label: _t("Wish"), css: "wish"} : {label: _t("Missing"), css: "missing"};
    }

    meta(item) {
        if (!item.year) {
            return "";
        }
        return item.upcoming ? _t("Expected in %s", item.year) : _t("Released in %s", item.year);
    }

    async gotIt(item) {
        await this.orm.call(API, "mobile_add", [item.work_id, "collection", item.edition_id]);
        this.notification.add(_t("Added to your collection."), {type: "success"});
        await this.load();
    }
}
