import {registry} from "@web/core/registry";
import {isBarcodeScannerSupported} from "@web/core/barcode/barcode_video_scanner";
import {isMobileOS} from "@web/core/browser/feature_detection";
import {CharField, charField} from "@web/views/fields/char/char_field";
import {scanIsbn} from "./isbn_scan_dialog";

/**
 * Widget `isbn_scan` (US-070) : champ texte + bouton caméra sur mobile pour
 * lire l'EAN-13 d'un album. Sans caméra (ou sur ordinateur), le champ reste
 * une saisie texte classique.
 */
export class IsbnScanField extends CharField {
    static template = "comics_collections.IsbnScanField";

    get hasScanButton() {
        return !this.props.readonly && isMobileOS() && isBarcodeScannerSupported();
    }

    async onScanClick() {
        const isbn = await scanIsbn(this.env);
        if (isbn) {
            await this.props.record.update({[this.props.name]: isbn});
        }
    }
}

export const isbnScanField = {
    ...charField,
    component: IsbnScanField,
    supportedTypes: ["char"],
};

registry.category("fields").add("isbn_scan", isbnScanField);
