# Copyright (c) 2025, Dexciss and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt
from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_details
from erpnext.accounts.doctype.bank_account.bank_account import get_bank_account_details

class BankTransactionLog(Document):
	def after_insert(self):
		frappe.enqueue(
			self.create_payment_entry, timeout=3000, Transaction_Date=self.transaction_date,Virtual_Account_No=self.virtual_account_no, Reference_No=self.reference_no, Amount=self.amount, Type=self.type
		)




	def create_payment_entry(self,Transaction_Date,Virtual_Account_No, Reference_No, Amount, Type):
		frappe.set_user("Administrator")
		try:
			# Get bank integration settings
			doc = frappe.get_doc("Bank Integration Setting")
			Acc_No = None
			auto_submit = 0
			company, cost_center, company_ba = None, None, None

			for config in doc.bank_configuration:
				company = config.company
				cost_center = config.cost_center
				company_ba = frappe.get_doc("Bank Account", {"name": config.bank_account})
				auto_submit += config.auto_submit_of_payment_entry

				if config.has_special_character == 1:
					Acc_No = Virtual_Account_No[:-5] + config.special_character + Virtual_Account_No[-5:]

			# Determine Customer ID
			customer_id = (Acc_No or Virtual_Account_No)[4:]

			# Validate Customer
			if not frappe.get_value("Customer", customer_id):
				frappe.local.response['http_status_code'] = 404
				return {"message": "Invalid Customer", "stts_flg": "N"}

			cus = frappe.get_doc("Customer", customer_id)
			party_type = "Customer"
			party = cus.name

			# Get account details
			party_details = get_party_details(company, party_type, party, Transaction_Date, cost_center)
			com_acc_details = get_bank_account_details(company_ba.name)

			# Format payment type
			payment_type_map = {"N": "NEFT", "R": "RTGS", "I": "IMPS"}
			types = payment_type_map.get(Type, Type)
			ref_no = f"{types}/{Reference_No}"

			# Check for non-cancelled duplicate
			existing_payment = frappe.get_value("Payment Entry", {
				"reference_no": ref_no,
				"docstatus": ["!=", 2]
			})
			if existing_payment:
				self.add_comment("Comment", f"This entry was skipped to avoid duplication. Existing Payment Entry: {existing_payment}")
				return {"message": "Duplicate Entry", "stts_flg": "N"}

			# Create Payment Entry
			payment_entry = frappe.new_doc("Payment Entry")
			payment_entry.update({
				"payment_type": "Receive",
				"party_type": "Customer",
				"posting_date": Transaction_Date,
				"paid_amount": flt(Amount),
				"received_amount": flt(Amount),
				"bank_account": company_ba.name,
				"party": cus.name,
				"party_name": party_details.get("party_name"),
				"paid_from": party_details.get("party_account"),
				"paid_from_account_currency": party_details.get("party_account_currency"),
				"paid_to_account_currency": party_details.get("party_account_currency"),
				"party_balance": party_details.get("party_balance"),
				"paid_from_account_balance": party_details.get("account_balance"),
				"paid_to": com_acc_details.get("account"),
				"reference_no": ref_no,
				"reference_date": Transaction_Date,
				"source_exchange_rate": 1,
				"target_exchange_rate": 1
			})

			if auto_submit == 1:
				payment_entry.flags.ignore_permissions = True
				payment_entry.insert(ignore_permissions=True)
				payment_entry.submit()
				self.db_set("payment_entry_created",1)
			else:
				payment_entry.insert(ignore_permissions=True)
				self.db_set("payment_entry_created",1)

			return {"message": "Payment Successful", "stts_flg": "Y"}

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Axis Bank Integration Payment Error")
			frappe.local.response['http_status_code'] = 500
			return {"message": "Payment Failed", "stts_flg": "N"}






def create_payment_entry_background():
	pa=frappe.db.sql("select * from `tabBank Transaction Log` where payment_entry_created=0 ",as_dict=1)

	for i in pa:
		Transaction_Date=i.get("transaction_date")
		Virtual_Account_No=i.get("virtual_account_no")
		Reference_No=i.get("reference_no")
		Amount=i.get("amount")
		Type=i.get("type")
		try:
			# Get bank integration settings
			doc = frappe.get_doc("Bank Integration Setting")
			Acc_No = None
			auto_submit = 0
			company, cost_center, company_ba = None, None, None

			for config in doc.bank_configuration:
				company = config.company
				cost_center = config.cost_center
				company_ba = frappe.get_doc("Bank Account", {"name": config.bank_account})
				auto_submit += config.auto_submit_of_payment_entry

				if config.has_special_character == 1:
					Acc_No = Virtual_Account_No[:-5] + config.special_character + Virtual_Account_No[-5:]

			# Determine Customer ID
			customer_id = (Acc_No or Virtual_Account_No)[4:]

			# Validate Customer
			if not frappe.get_value("Customer", customer_id):
				continue

			cus = frappe.get_doc("Customer", customer_id)
			party_type = "Customer"
			party = cus.name

			# Get account details
			party_details = get_party_details(company, party_type, party, Transaction_Date, cost_center)
			com_acc_details = get_bank_account_details(company_ba.name)

			# Format payment type
			payment_type_map = {"N": "NEFT", "R": "RTGS", "I": "IMPS"}
			types = payment_type_map.get(Type, Type)
			ref_no = f"{types}/{Reference_No}"

			# Check for non-cancelled duplicate
			existing_payment = frappe.get_value("Payment Entry", {
				"reference_no": ref_no,
				"docstatus": ["!=", 2]
			})
			if existing_payment:
				frappe.db.set_value("Bank Transaction Log", i.get("name"), "payment_entry_created", 1)
				frappe.get_doc("Bank Transaction Log", i.get("name")).add_comment("Comment", f"This entry was skipped to avoid duplication. Existing Payment Entry: {existing_payment}")
				continue

			# Create Payment Entry
			payment_entry = frappe.new_doc("Payment Entry")
			payment_entry.update({
				"payment_type": "Receive",
				"party_type": "Customer",
				"posting_date": Transaction_Date,
				"paid_amount": flt(Amount),
				"received_amount": flt(Amount),
				"bank_account": company_ba.name,
				"party": cus.name,
				"party_name": party_details.get("party_name"),
				"paid_from": party_details.get("party_account"),
				"paid_from_account_currency": party_details.get("party_account_currency"),
				"paid_to_account_currency": party_details.get("party_account_currency"),
				"party_balance": party_details.get("party_balance"),
				"paid_from_account_balance": party_details.get("account_balance"),
				"paid_to": com_acc_details.get("account"),
				"reference_no": ref_no,
				"reference_date": Transaction_Date,
				"source_exchange_rate": 1,
				"target_exchange_rate": 1
			})

			if auto_submit == 1:
				payment_entry.flags.ignore_permissions = True
				payment_entry.insert(ignore_permissions=True)
				payment_entry.submit()
				frappe.db.set_value("Bank Transaction Log", i.get("name"), "payment_entry_created", 1)
			else:
				payment_entry.insert(ignore_permissions=True)
				frappe.db.set_value("Bank Transaction Log", i.get("name"), "payment_entry_created", 1)

		except Exception:
			frappe.log_error(frappe.get_traceback(), "Axis Bank Integration Payment Error")
