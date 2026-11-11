/** @odoo-module */
import {Component, onWillStart, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {ComicCover} from "../cover";
import {NEXT_READING, readingLabel, serieColor} from "../utils";

const API = "comic.mobile.api";

export class SerieScreen extends Component {
    static template = "comic_mobile.SerieScreen";
    static components = {ComicCover};
    static props = {serieId: Number, back: Function};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({serie: null});
        onWillStart(() => this.load());
    }

    async load() {
        this.state.serie = await this.orm.call(API, "mobile_get_serie", [this.props.serieId]);
    }

    get color() {
        return serieColor(this.state.serie && this.state.serie.name);
    }

    get progress() {
        const s = this.state.serie;
        return s.total ? Math.round((100 * s.owned) / s.total) : 0;
    }

    get kicker() {
        const s = this.state.serie;
        return [s.genre, s.status].filter(Boolean).join(" · ");
    }

    get countLabel() {
        const s = this.state.serie;
        return _t("%(owned)s of %(total)s volumes", {owned: s.owned, total: s.total});
    }

    get readLabel() {
        return _t("%s read", this.state.serie.read);
    }

    readingLabel(album) {
        return readingLabel(album.reading);
    }

    async toggleFollow() {
        const res = await this.orm.call(API, "mobile_set_follow", [this.state.serie.id, !this.state.serie.followed]);
        this.state.serie.followed = res.followed;
    }

    async markOwned(album) {
        await this.orm.call(API, "mobile_add", [album.work_id, "collection", album.edition_id]);
        this.notification.add(_t("Added to your collection."), {type: "success"});
        await this.load();
    }

    async cycleReading(album) {
        const res = await this.orm.call(API, "mobile_set_reading", [album.work_id, NEXT_READING[album.reading] || "lu"]);
        Object.assign(album, res);
        await this.load();
    }
}
