// Copyright (c) 2022, Dexciss and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bank Integration Setting', {
	setup: function(frm) {
		frm.set_query('bank_account', 'bank_configuration',  function() {
			return {
				filters: {
					is_company_account: 1
				}
			}
		})
	}
});