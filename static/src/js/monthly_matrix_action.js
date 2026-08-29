/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

const MONTH_NAMES = {
    "1": "January", "2": "February", "3": "March", "4": "April",
    "5": "May", "6": "June", "7": "July", "8": "August",
    "9": "September", "10": "October", "11": "November", "12": "December",
};

function fmt(n) {
    return (n || 0).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

export class ExpenseMonthlyMatrix extends Component {
    static template = "expense_tracker.MonthlyMatrix";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, categories: [], rows: [], totals: null });
        onWillStart(() => this.loadData());
    }

    /** Rebuilds the matrix from current data. Income categories are read live
     * from expense.tracker.category, so newly added/renamed/archived
     * categories are picked up automatically - no code change needed. */
    async loadData() {
        this.state.loading = true;

        const categories = await this.orm.searchRead(
            "expense.tracker.category",
            [["type", "=", "income"], ["active", "=", true]],
            ["id", "name"],
            { order: "sequence, name" }
        );

        const monthlyRecords = await this.orm.searchRead(
            "expense.tracker.monthly",
            [],
            ["city_id", "manager_id", "month", "year", "total_income", "total_expense", "net_income"],
            { order: "year desc, month desc, city_id" }
        );

        const byMonthly = {};
        if (monthlyRecords.length && categories.length) {
            const groups = await this.orm.readGroup(
                "expense.tracker.line",
                [["line_type", "=", "income"], ["monthly_id", "in", monthlyRecords.map((m) => m.id)]],
                ["amount:sum"],
                ["monthly_id", "category_id"],
                { lazy: false }
            );
            for (const g of groups) {
                const monthlyId = g.monthly_id[0];
                const catId = g.category_id[0];
                byMonthly[monthlyId] = byMonthly[monthlyId] || {};
                byMonthly[monthlyId][catId] = g.amount || 0;
            }
        }

        const rows = monthlyRecords.map((m) => ({
            id: m.id,
            city: m.city_id ? m.city_id[1] : "",
            manager: m.manager_id ? m.manager_id[1] : "",
            month: MONTH_NAMES[String(m.month)] || m.month,
            year: m.year,
            cats: categories.map((c) => fmt((byMonthly[m.id] || {})[c.id] || 0)),
            total_income: fmt(m.total_income),
            total_expense: fmt(m.total_expense),
            net_income: fmt(m.net_income),
        }));

        const catTotals = categories.map((c) =>
            fmt(monthlyRecords.reduce((s, m) => s + ((byMonthly[m.id] || {})[c.id] || 0), 0))
        );
        const totals = {
            cats: catTotals,
            total_income: fmt(monthlyRecords.reduce((s, m) => s + (m.total_income || 0), 0)),
            total_expense: fmt(monthlyRecords.reduce((s, m) => s + (m.total_expense || 0), 0)),
            net_income: fmt(monthlyRecords.reduce((s, m) => s + (m.net_income || 0), 0)),
        };

        this.state.categories = categories;
        this.state.rows = rows;
        this.state.totals = totals;
        this.state.loading = false;
    }

    openRecord(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "expense.tracker.monthly",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("actions").add("expense_tracker_monthly_matrix", ExpenseMonthlyMatrix);
