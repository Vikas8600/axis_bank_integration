frappe.ui.form.on("Mosambee Transaction Log", {
	refresh(frm) {
		$('.layout-side-section').hide();

		const is_system_manager = frappe.user.has_role("System Manager");

		if (is_system_manager && !frm.is_new() && !frm.doc.payment_entry && frm.doc.status === "Failed") {
			frm.add_custom_button(__("Retry Payment"), () => {
				frappe.confirm(__("Retry payment processing for this log?"), () => {
					frappe.call({
						method: "axis_bank_integration.mosambee.retry_payment",
						args: { log_name: frm.doc.name },
						freeze: true,
						freeze_message: __("Retrying payment..."),
						callback: (r) => {
							if (!r.message) return;
							if (r.message.payment_entry) {
								frappe.show_alert({
									message: __("Payment Entry created: {0}", [r.message.payment_entry]),
									indicator: "green",
								});
							} else {
								frappe.msgprint({
									title: __("Retry Failed"),
									message: r.message.error_message || __("Status: {0}", [r.message.status]),
									indicator: "red",
								});
							}
							frm.reload_doc();
						},
					});
				});
			}).addClass("btn-primary");
		}
	}
});
