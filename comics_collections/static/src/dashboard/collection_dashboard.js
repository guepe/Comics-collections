import {Component, onWillStart, useState} from "@odoo/owl";
import {_t} from "@web/core/l10n/translation";
import {registry} from "@web/core/registry";
import {Layout} from "@web/search/layout";
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
    static components = {Layout};
    static props = {...standardActionServiceProps};

    setup() {
        // Panneau de contrôle Odoo standard (fil d'Ariane), sans barre de recherche
        this.display = {controlPanel: {}};
        this.readingColors = {non_lu: "bg-secondary", en_cours: "bg-info", lu: "bg-success"};
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

    get kpis() {
        const data = this.state.data;
        const plural = (count, singular, pluralForm) =>
            count > 1 ? pluralForm.replace("%s", count) : singular.replace("%s", count);
        return [
            {
                key: "nb_albums",
                label: _t("Albums owned"),
                value: data.nb_albums,
                hint: _t("View my collection"),
                icon: "fa-book",
                color: "primary",
                onClick: () => this.openAlbums(),
            },
            {
                key: "nb_wishlist",
                label: _t("Wishlist"),
                value: data.nb_wishlist,
                hint: `${plural(data.nb_manques, _t("%s missing volume"), _t("%s missing volumes"))} · ${plural(
                    data.nb_souhaits,
                    _t("%s wish"),
                    _t("%s wishes")
                )}`,
                icon: "fa-heart",
                color: "danger",
                onClick: () => this.openWishlist(),
            },
            {
                key: "nb_series",
                label: _t("Series"),
                value: data.nb_series,
                // Pas de pluriel distinct en anglais pour « series » : libellés « Completed: n »
                hint: _t("Completed: %(completed)s · Ongoing: %(ongoing)s")
                    .replace("%(completed)s", data.series_completes)
                    .replace("%(ongoing)s", data.series_en_cours),
                icon: "fa-th-large",
                color: "info",
                onClick: () => this.openSeries(),
            },
            {
                key: "loans_late",
                label: _t("Overdue loans"),
                value: data.loans_late,
                hint: data.loans_late ? _t("To get back") : _t("None overdue"),
                icon: "fa-exchange",
                color: data.loans_late ? "warning" : "success",
                alert: data.loans_late > 0,
                onClick: () => this.openLoans(),
            },
        ];
    }

    openCatalogue() {
        // Collection privée (US-087) : le catalogue complet est réservé au gestionnaire
        // dans le cœur ; on ouvre « Mes albums » directement en création.
        this.action.doAction("comics_collections.action_comic_work", {viewType: "form"});
    }

    openAlbums() {
        this.action.doAction("comics_collections.action_comic_work");
    }

    openWishlist() {
        this.action.doAction("comics_collections.action_comic_wishlist");
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

    exportCsv() {
        this.action.doAction({
            type: "ir.actions.act_url",
            url: "/comics/collection/export.csv",
            target: "download",
        });
    }

    async printInventory() {
        const action = await this.orm.call("comic.customer.album", "action_print_my_inventory", []);
        await this.action.doAction(action);
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
