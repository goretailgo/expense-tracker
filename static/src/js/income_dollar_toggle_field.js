/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, reactive } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/* Shared across every cell using this widget on the page, so one click
 * converts the whole column at once. This is purely a display toggle:
 * nothing is written back to the record, the database, or any total_income
 * value - it only changes how the number is formatted on screen. */
const currencyToggleState = reactive({ showDollar: false, rate: null });

export class IncomeDollarToggleField extends Component {
    static template = "expense_tracker.IncomeDollarToggleField";
    static props = { ...standardFieldProps };

    setup() {
        this.curr = useState(currencyToggleState);
    }

    get displayValue() {
        const raw = this.props.record.data[this.props.name] || 0;
        if (this.curr.showDollar && this.curr.rate) {
            return "$ " + (raw / this.curr.rate).toLocaleString("en-US", {
                minimumFractionDigits: 2, maximumFractionDigits: 2,
            });
        }
        return "₹ " + raw.toLocaleString("en-IN", {
            minimumFractionDigits: 2, maximumFractionDigits: 2,
        });
    }

    onToggleClick(ev) {
        ev.stopPropagation();
        if (!this.curr.showDollar) {
            const input = window.prompt(
                "Enter the INR → USD rate to display Total Income in dollars\n" +
                "(display only - nothing is saved or recalculated in the data):",
                this.curr.rate || "83.5"
            );
            if (input === null) {
                return;
            }
            const rate = parseFloat(input);
            if (!rate || rate <= 0) {
                window.alert("Please enter a valid positive rate.");
                return;
            }
            this.curr.rate = rate;
            this.curr.showDollar = true;
        } else {
            this.curr.showDollar = false;
        }
    }
}

registry.category("fields").add("income_dollar_toggle", {
    component: IncomeDollarToggleField,
    supportedTypes: ["monetary"],
});
