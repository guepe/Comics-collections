/** @odoo-module */
import {Component, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {useService} from "@web/core/utils/hooks";
import {BarcodeVideoScanner, isBarcodeScannerSupported} from "@web/core/barcode/barcode_video_scanner";
import {extractIsbn13} from "@comics_collections/isbn_scan/isbn_scan_dialog";
import {ComicCover} from "../cover";

const API = "comic.mobile.api";

/**
 * Scan d'un ISBN : caméra (scanner vidéo d'Odoo, ZXing si le navigateur n'a pas de
 * BarcodeDetector, comme Safari) ou saisie manuelle, puis fiche de résultat.
 */
export class ScanScreen extends Component {
    static template = "comic_mobile.ScanScreen";
    static components = {BarcodeVideoScanner, ComicCover};
    static props = {close: Function, openSerie: Function};

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.busy = false;
        this.state = useState({
            camera: isBarcodeScannerSupported(),
            cameraError: "",
            rejected: "",
            manual: "",
            loading: false,
            result: null,
        });
    }

    get statusInfo() {
        const r = this.state.result;
        if (!r) {
            return {};
        }
        return {
            owned: {label: _t("You own it"), css: "owned"},
            wished: {label: _t("In your wishlist"), css: "wished"},
            missing: {label: _t("You're missing it"), css: "missing"},
            unknown: {label: _t("Not in the catalogue"), css: "unknown"},
        }[r.status];
    }

    get stripHint() {
        const r = this.state.result;
        if (!r || !r.serie_total) {
            return "";
        }
        if (r.status === "owned") {
            return _t("Already on your shelf.");
        }
        if (r.is_next) {
            return _t("It's the next volume: it continues your series.");
        }
        return r.serie_owned ? _t("It fills a gap in your series.") : _t("You don't own this series yet.");
    }

    onCameraResult(code) {
        if (this.busy || this.state.result) {
            return;
        }
        const isbn = extractIsbn13(code);
        if (!isbn) {
            this.state.rejected = String(code || "");
            return;
        }
        this.lookup(isbn);
    }

    onCameraError(error) {
        this.state.camera = false;
        this.state.cameraError = error.message;
    }

    onManualInput(ev) {
        this.state.manual = ev.target.value;
    }

    onManualSubmit(ev) {
        ev.preventDefault();
        if (this.state.manual.trim()) {
            this.lookup(this.state.manual.trim());
        }
    }

    async lookup(isbn) {
        this.busy = true;
        this.state.loading = true;
        this.state.rejected = "";
        try {
            this.state.result = await this.orm.call(API, "mobile_scan", [isbn]);
        } finally {
            this.state.loading = false;
            this.busy = false;
        }
    }

    async add(target) {
        const r = this.state.result;
        this.state.result = await this.orm.call(API, "mobile_add", [r.work_id, target, r.edition_id]);
        this.notification.add(
            target === "collection" ? _t("Added to your collection.") : _t("Added to your wishlist."),
            {type: "success"}
        );
    }

    scanAgain() {
        this.state.result = null;
        this.state.manual = "";
    }
}
