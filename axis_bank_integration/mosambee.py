import hashlib
import json

import frappe
from frappe.utils import flt, getdate


@frappe.whitelist()
def receive_transaction(**kwargs):
	"""
	Webhook endpoint for Mosambee Payment Transaction Posting.
	Mosambee sends transaction data here after every payment on the POS device.

	URL to give Mosambee:
	https://<your-site>/api/method/axis_bank_integration.mosambee.receive_transaction
	"""
	data = kwargs
	raw_json = json.dumps(data, indent=2)

	# STEP 0: Save raw JSON immediately before any processing
	log = None
	try:
		log = frappe.new_doc("Mosambee Transaction Log")
		log.status = "Pending"
		log.raw_data = raw_json
		log.transaction_id = data.get("transactionID") or data.get("transactionId") or ""
		log.transaction_amount = flt(data.get("transactionAmount", 0))
		log.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		frappe.log_error(title="Mosambee Raw Log Error", message=frappe.get_traceback())

	try:
		try:
			settings = frappe.get_doc("Mosambee Settings")
		except Exception:
			settings = None

		transaction_id = data.get("transactionID") or data.get("transactionId") or ""
		response_code = str(data.get("responseCode", ""))

		# Determine if transaction is approved
		is_approved = response_code in ("0", "00", "000")

		# Validate checksum
		checksum_valid = False
		if settings:
			salt_value = settings.get_password("salt_value") if settings.salt_value else None
			if salt_value:
				checksum_valid = validate_checksum(data, salt_value)

		# STEP 1: Update log with all parsed fields
		if log:
			status = "Declined" if not is_approved else "Pending"
			populate_log_fields(log, data, status, checksum_valid)
			log.save(ignore_permissions=True)
			frappe.db.commit()

		# STEP 2: Find customer and create payment entry
		if is_approved and log and settings and settings.enabled:
			try:
				customer_id_field = settings.customer_id_field or "billNumber"
				customer_id_value = str(data.get(customer_id_field, "")).strip()
				customer = None
				if customer_id_value:
					customer = frappe.db.get_value("Customer", {"name": customer_id_value}, "name")
					if not customer:
						customer = frappe.db.get_value("Customer", {"customer_name": customer_id_value}, "name")

				if customer:
					log.customer = customer
					pe_name = create_payment_entry(log, settings)
					log.status = "Payment Created"
					log.payment_entry = pe_name
				else:
					log.error_message = f"Customer not found for {customer_id_field}: {customer_id_value}"

				log.save(ignore_permissions=True)
				frappe.db.commit()
			except Exception:
				log.status = "Failed"
				log.error_message = frappe.get_traceback()
				log.save(ignore_permissions=True)
				frappe.db.commit()
				frappe.log_error(
					title=f"Mosambee Payment Entry Error - {transaction_id}",
					message=frappe.get_traceback()
				)

		return {"status": 200, "message": "success", "merchant_refTxnId": data.get("billNumber", "")}

	except Exception:
		frappe.log_error(title="Mosambee Webhook Error", message=frappe.get_traceback())
		if log:
			try:
				log.reload()
				log.status = "Failed"
				log.error_message = frappe.get_traceback()
				log.save(ignore_permissions=True)
				frappe.db.commit()
			except Exception:
				pass
		return {"status": 200, "message": "success"}


def populate_log_fields(log, data, status, checksum_valid):
	"""Populate all parsed fields on an existing log document."""
	log.status = status
	log.transaction_id = data.get("transactionID") or data.get("transactionId") or ""
	log.transaction_date = data.get("transactionDate", "")
	log.transaction_time = data.get("transactionTime", "")
	log.transaction_amount = flt(data.get("transactionAmount", 0))
	log.transaction_status = data.get("transactionStatus", "")
	log.response_code = str(data.get("responseCode", ""))
	log.transaction_type_name = data.get("transactionTypeName", "")
	log.transaction_rrn = data.get("transactionRRN", "")
	log.card_type = data.get("cardType", "")
	log.card_holder_name = data.get("cardHolderName", "")
	log.transaction_card_number = data.get("transactionCardNumber", "")
	log.credit_debit_card_type = data.get("creditDebitCardType", "")
	log.transaction_auth_code = data.get("transactionAuthCode", "")
	log.transaction_mode = data.get("transactionMode", "")
	log.acquirer_name = data.get("acquirerName", "")
	log.name1 = data.get("name", "")
	log.merchant_id = data.get("merchantId", "")
	log.business_name = data.get("businessName", "")
	log.transaction_terminal_id = data.get("transactionTerminalId", "")
	log.invoice_number = data.get("invoiceNumber", "")
	log.bill_number = data.get("billNumber", "")
	log.narration = data.get("narration", "")
	log.tg_transaction_id = data.get("tgTransactionId", "")
	log.transaction_stan = data.get("transactionSTAN", "")
	log.transaction_batch_number = data.get("transactionBatchNumber", "")
	log.ref_txn_id = data.get("refTxnId", "")
	log.transaction_lat = data.get("transactionLat", "")
	log.transaction_long = data.get("transactionLong", "")
	log.address_line1 = data.get("addressLine1", "")
	log.address_line2 = data.get("addressLine2", "")
	log.checksum = data.get("checksum", "")
	log.checksum_valid = 1 if checksum_valid else 0


def validate_checksum(data, salt_value):
	"""Validate checksum using SHA-512(transactionId + merchantId + transactionRRN + salt)"""
	transaction_id = str(data.get("transactionID") or data.get("transactionId") or "")
	merchant_id = str(data.get("merchantId", ""))
	transaction_rrn = str(data.get("transactionRRN", ""))

	raw_string = transaction_id + merchant_id + transaction_rrn + salt_value
	computed_checksum = hashlib.sha512(raw_string.encode()).hexdigest()

	received_checksum = str(data.get("checksum", ""))
	return computed_checksum.lower() == received_checksum.lower()


def create_payment_entry(log, settings):
	"""Create a Payment Entry from a Mosambee transaction log"""
	company = settings.default_company
	if not company:
		company = frappe.defaults.get_defaults().get("company")

	mode_of_payment = settings.default_mode_of_payment
	if not mode_of_payment:
		card_type = (log.card_type or "").upper()
		if "UPI" in card_type or "RUPAY" in card_type:
			mode_of_payment = frappe.db.get_value("Mode of Payment", {"name": ["like", "%UPI%"]}, "name")
		if not mode_of_payment:
			mode_of_payment = frappe.db.get_value("Mode of Payment", {"name": ["like", "%Bank%"]}, "name")
		if not mode_of_payment:
			mode_of_payment = "Bank Draft"

	paid_to = settings.default_paid_to_account
	if not paid_to:
		paid_to = frappe.db.get_value(
			"Mode of Payment Account",
			{"parent": mode_of_payment, "company": company},
			"default_account"
		)

	txn_date = None
	if log.transaction_date:
		try:
			txn_date = getdate(log.transaction_date)
		except Exception:
			txn_date = frappe.utils.today()
	else:
		txn_date = frappe.utils.today()

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = log.customer
	pe.company = company
	pe.posting_date = txn_date
	pe.paid_amount = log.transaction_amount
	pe.received_amount = log.transaction_amount
	pe.mode_of_payment = mode_of_payment
	pe.reference_no = log.transaction_rrn or log.transaction_id
	pe.reference_date = txn_date

	if paid_to:
		pe.paid_to = paid_to

	pe.remarks = (
		f"Payment received via Mosambee POS Device.\n"
		f"Transaction ID: {log.transaction_id}\n"
		f"RRN: {log.transaction_rrn}\n"
		f"Card: {log.card_type} {log.transaction_card_number}\n"
		f"Card Holder: {log.card_holder_name}"
	)

	pe.insert(ignore_permissions=True)
	# pe.submit()

	return pe.name
