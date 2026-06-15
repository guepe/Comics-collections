/** @odoo-module **/

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BookingDashboard extends Component {
  setup() {
    this.orm = useService("orm");
    this.action = useService("action");

    this.state = useState({
      approved: 0,
      pending: 0,
      total: 0,
      total_books: 0,
      total_category: 0,
      clickCount: 0,
    });

    onWillStart(async () => {
      await this.loadCounts();
    });
  }

  incrementCounter() {
    this.state.clickCount++;
  }
  resetCounter() {
    this.state.clickCount = 0;
  }

  async loadCounts() {
    this.state.approved = await this.orm.searchCount("booking.history", [
      ["status", "=", "approved"],
    ]);

    this.state.pending = await this.orm.searchCount("booking.history", [
      ["status", "=", "pending"],
    ]);

    this.state.total = await this.orm.searchCount("booking.history", []);

    this.state.total_books = await this.orm.searchCount("book.books", []);
    this.state.total_category = await this.orm.searchCount("book.category", []);
  }

  async openApproved() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Approved Bookings",
      res_model: "booking.history",
      views: [[false, "list"]],
      domain: [["status", "=", "approved"]],
      target: "new",
      context: {
        create: false,
      },
    });
  }

  openPending() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "Pending Bookings",
      res_model: "booking.history",
      views: [[false, "list"]],
      domain: [["status", "=", "pending"]],
      target: "new",
      context: {
        create: false,
      },
    });
  }

  async openBooks() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "All Books",
      res_model: "book.books",
      views: [[false, "list"]],
      target: "new",
      context: {
        create: false,
      },
    });
  }

  async openCategory() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "All Category List",
      res_model: "book.category",
      views: [[false, "list"]],
      target: "new",
      context: {
        create: false,
      },
    });
  }

  openAll() {
    this.action.doAction({
      type: "ir.actions.act_window",
      name: "All Booking History",
      res_model: "booking.history",
      views: [[false, "list"]],
      target: "new",
      context: {
        create: false,
      },
    });
  }
}

BookingDashboard.template = "wk_library_management.Dashboard";

registry.category("actions").add("booking_dashboard_action", BookingDashboard);
