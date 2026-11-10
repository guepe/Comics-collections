import {Component, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {Dialog} from "@web/core/dialog/dialog";
import {BarcodeVideoScanner, isBarcodeScannerSupported} from "@web/core/barcode/barcode_video_scanner";

/**
 * Scan d'ISBN à la caméra (US-070).
 *
 * Réutilise le scanner vidéo d'Odoo (BarcodeDetector natif, sinon ZXing chargé
 * à la demande) mais n'accepte que les EAN-13 d'ISBN (préfixe 978/979, clé
 * valide) : tout autre code lu est signalé et le scan continue.
 * Partagé entre le back-office (widget isbn_scan) et le portail (comic_shop).
 */

/**
 * Retourne l'ISBN-13 (chiffres seuls) si `raw` est un EAN-13 d'ISBN valide,
 * sinon une chaîne vide.
 *
 * @param {String} raw code lu
 * @returns {String}
 */
export function extractIsbn13(raw) {
    const digits = String(raw || "").replace(/[\s-]/g, "");
    if (!/^97[89]\d{10}$/.test(digits)) {
        return "";
    }
    let total = 0;
    for (let i = 0; i < 12; i++) {
        total += Number(digits[i]) * (i % 2 ? 3 : 1);
    }
    return (10 - (total % 10)) % 10 === Number(digits[12]) ? digits : "";
}

export class IsbnScanDialog extends Component {
    static template = "comics_collections.IsbnScanDialog";
    static components = {BarcodeVideoScanner, Dialog};
    static props = ["close", "onResult"];

    setup() {
        this.done = false;
        this.state = useState({
            supported: isBarcodeScannerSupported(),
            errorMessage: _t("The camera is not accessible (permission denied or insecure connection)."),
            rejected: "",
        });
    }

    onResult(code) {
        if (this.done) {
            return;
        }
        const isbn = extractIsbn13(code);
        if (!isbn) {
            this.state.rejected = String(code || "");
            return;
        }
        this.done = true;
        this.props.onResult(isbn);
        this.props.close();
    }

    onError(error) {
        this.state.supported = false;
        this.state.errorMessage = error.message;
    }
}

/**
 * Ouvre le dialogue de scan ; résout avec l'ISBN-13 lu, ou "" si l'utilisateur
 * ferme le dialogue (ou si la caméra est indisponible).
 *
 * @param {Object} env environnement OWL (doit fournir le service dialog)
 * @returns {Promise<String>}
 */
export function scanIsbn(env) {
    return new Promise((resolve) => {
        env.services.dialog.add(IsbnScanDialog, {onResult: resolve}, {onClose: () => resolve("")});
    });
}
