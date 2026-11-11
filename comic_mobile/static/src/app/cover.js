/** @odoo-module */
import {Component} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {readingLabel, serieColor} from "./utils";

/** Couverture d'album : image si disponible, sinon aplat aux couleurs de la série. */
export class ComicCover extends Component {
    static template = "comic_mobile.Cover";
    static props = {
        album: Object,
        showReading: {type: Boolean, optional: true},
        small: {type: Boolean, optional: true},
    };

    get color() {
        return serieColor(this.props.album.serie);
    }

    get tomeLabel() {
        return this.props.album.tome ? _t("Vol. %s", this.props.album.tome) : "";
    }

    get readingLabel() {
        return readingLabel(this.props.album.reading);
    }
}
