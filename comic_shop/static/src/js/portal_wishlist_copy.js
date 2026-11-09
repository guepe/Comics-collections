import {Interaction} from "@web/public/interaction";
import {registry} from "@web/core/registry";

/**
 * Bouton « Copier » du lien de wishlist partagée (US-073).
 *
 * navigator.clipboard n'existe qu'en contexte sécurisé (HTTPS ou localhost) :
 * sur un site en HTTP, on retombe sur la sélection du champ + execCommand("copy"),
 * et à défaut le lien reste sélectionné pour un Ctrl/Cmd+C manuel.
 */
export class PortalWishlistCopy extends Interaction {
    static selector = ".o_comic_wishlist_copy";

    dynamicContent = {
        ".o_comic_wishlist_copy_input": {"t-on-focus": this.selectLink},
        ".o_comic_wishlist_copy_btn": {"t-on-click": this.onCopy},
    };

    setup() {
        this.input = this.el.querySelector(".o_comic_wishlist_copy_input");
        this.button = this.el.querySelector(".o_comic_wishlist_copy_btn");
    }

    selectLink() {
        this.input.select();
    }

    async onCopy() {
        const value = this.input.value;
        let copied = false;
        if (navigator.clipboard && window.isSecureContext) {
            try {
                await this.waitFor(navigator.clipboard.writeText(value));
                copied = true;
            } catch {
                copied = false;
            }
        }
        if (!copied) {
            this.input.focus();
            this.input.select();
            this.input.setSelectionRange(0, value.length);
            try {
                copied = document.execCommand("copy");
            } catch {
                copied = false;
            }
        }
        this.button.textContent = copied ? "Copié ✓" : "Sélectionné : Ctrl+C";
    }
}

registry.category("public.interactions").add("comic_shop.portal_wishlist_copy", PortalWishlistCopy);
