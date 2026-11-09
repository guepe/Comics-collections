import {Interaction} from "@web/public/interaction";
import {registry} from "@web/core/registry";
import {isBarcodeScannerSupported} from "@web/core/barcode/barcode_video_scanner";
import {scanIsbn} from "@comics_collections/isbn_scan/isbn_scan_dialog";

/**
 * Bouton « Scanner » de /my/library/add (US-070).
 *
 * Le bouton est rendu masqué (d-none) : il n'apparaît que si le navigateur
 * expose la caméra (navigator.mediaDevices.getUserMedia, donc HTTPS ou
 * localhost). Sinon un message invite à la saisie manuelle, qui reste
 * toujours possible. L'ISBN lu remplit le champ et lance la recherche habituelle.
 */
export class PortalIsbnScan extends Interaction {
    static selector = ".o_comic_isbn_scan";

    dynamicContent = {
        ".o_comic_isbn_scan_btn": {
            "t-on-click": this.onScanClick,
            "t-att-class": () => ({"d-none": !this.supported}),
        },
        ".o_comic_isbn_scan_unavailable": {
            "t-att-class": () => ({"d-none": this.supported}),
        },
    };

    setup() {
        this.supported = isBarcodeScannerSupported();
    }

    async onScanClick() {
        const isbn = await this.waitFor(scanIsbn(this.env));
        if (!isbn) {
            return;
        }
        this.el.querySelector("input[name='isbn']").value = isbn;
        const titleInput = this.el.querySelector("input[name='title']");
        if (titleInput) {
            titleInput.value = "";
        }
        this.el.requestSubmit();
    }
}

registry.category("public.interactions").add("comic_shop.portal_isbn_scan", PortalIsbnScan);
