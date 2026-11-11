/** @odoo-module */
import {Component, onWillStart, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {useDebounced} from "@web/core/utils/timing";
import {ComicCover} from "../cover";

const API = "comic.mobile.api";

export class CollectionScreen extends Component {
    static template = "comic_mobile.CollectionScreen";
    static components = {ComicCover};
    static props = {openSerie: Function};

    setup() {
        this.orm = useService("orm");
        this.state = useState({reading: "all", search: "", albums: [], total: 0, loading: true, summary: {}});
        this.filters = [
            {key: "all", label: _t("All")},
            {key: "lu", label: _t("Read")},
            {key: "en_cours", label: _t("Reading")},
            {key: "non_lu", label: _t("Unread")},
        ];
        this.debouncedLoad = useDebounced(() => this.load(), 300);
        onWillStart(async () => {
            this.state.summary = await this.orm.call(API, "mobile_get_summary", []);
            await this.load();
        });
    }

    get subtitle() {
        const s = this.state.summary;
        return _t("%(albums)s albums · %(series)s series", {albums: s.albums || 0, series: s.series || 0});
    }

    async load(more = false) {
        this.state.loading = true;
        const res = await this.orm.call(API, "mobile_get_collection", [], {
            reading: this.state.reading,
            search: this.state.search,
            offset: more ? this.state.albums.length : 0,
        });
        this.state.albums = more ? [...this.state.albums, ...res.albums] : res.albums;
        this.state.total = res.total;
        this.state.loading = false;
    }

    setReading(key) {
        this.state.reading = key;
        this.load();
    }

    onSearch(ev) {
        this.state.search = ev.target.value;
        this.debouncedLoad();
    }
}
