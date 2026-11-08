import {Component, onWillStart, useState} from "@odoo/owl";
import {registry} from "@web/core/registry";
import {standardActionServiceProps} from "@web/webclient/actions/action_service";
import {useService} from "@web/core/utils/hooks";

/**
 * Tableau de bord collectionneur (US-065).
 *
 * Affiche tel quel le résultat de comic.customer.album.get_dashboard_data() :
 * aucun calcul de statistique côté client.
 */
export class CollectionDashboard extends Component {
    static template = "comics_collections.CollectionDashboard";
    static props = {...standardActionServiceProps};

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({data: null});
        onWillStart(async () => {
            this.state.data = await this.orm.call("comic.customer.album", "get_dashboard_data", []);
        });
    }

    get isEmpty() {
        const data = this.state.data;
        return !data.nb_albums && !data.nb_wishlist;
    }

    openAlbums() {
        this.action.doAction("comics_collections.action_comic_work");
    }

    openWishlist() {
        this.action.doAction("comics_collections.action_comic_my_library", {
            additionalContext: {search_default_collection: 0, search_default_wishlist: 1},
        });
    }

    openSeries() {
        this.action.doAction("comics_collections.action_comic_serie");
    }

    openLoans() {
        const context = this.state.data.loans_late
            ? {search_default_en_cours: 0, search_default_en_retard: 1}
            : {};
        this.action.doAction("comics_collections.action_comic_pret", {additionalContext: context});
    }

    openImport() {
        this.action.doAction("comics_collections.action_comic_import_wizard");
    }

    openRecord(resModel, resId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: resModel,
            res_id: resId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    formatDate(isoDate) {
        if (!isoDate) {
            return "";
        }
        const [year, month, day] = isoDate.split("-");
        return `${day}/${month}/${year}`;
    }
}

registry.category("actions").add("comic_collection_dashboard", CollectionDashboard);
