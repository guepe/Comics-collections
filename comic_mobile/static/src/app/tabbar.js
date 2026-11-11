/** @odoo-module */
import {Component} from "@odoo/owl";

export class ComicTabBar extends Component {
    static template = "comic_mobile.TabBar";
    static props = {current: String, onSelect: Function};
}
