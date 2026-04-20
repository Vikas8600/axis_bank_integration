import hashlib
import json

import frappe
from frappe.utils import flt


@frappe.whitelist(allow_guest=True)
def receive_transaction(**kwargs):
	data = kwargs
	raw_json = json.dumps(data, indent=2)

	settings = frappe.get_doc("Mosambee Settings")

	response_code = str(data.get("responseCode", ""))
	is_approved = response_code in ("0", "00", "000")

	checksum_valid = False
	salt_value = settings.get_password("salt_value") if settings.salt_value else None
	if salt_value:
		checksum_valid = validate_checksum(data, salt_value)

	customer_id_field = settings.customer_id_field or "billNumber"
	customer_id_value = str(data.get(customer_id_field, "")).strip()

	log = frappe.new_doc("Mosambee Transaction Log")
	log.raw_data = raw_json
	log.status = "Declined" if not is_approved else "Pending"
	populate_log_fields(log, data, checksum_valid)
	if customer_id_value:
		log.customer = customer_id_value
	log.insert(ignore_permissions=True)
	frappe.db.commit()

	if is_approved and settings.enabled and customer_id_value:
		frappe.enqueue(
			process_payment,
			queue="long",
			log_name=log.name,
			now=frappe.flags.in_test,
			at_front=True
		)

	return {"status": 200, "message": "success", "merchant_refTxnId": log.name if log else ""}


def process_payment(log_name):
	frappe.set_user("Administrator")
	log = frappe.get_doc("Mosambee Transaction Log", log_name)

	if log.payment_entry:
		return

	if not log.customer:
		log.status = "Failed"
		log.error_message = "No customer value set on log"
		log.save(ignore_permissions=True)
		frappe.db.commit()
		return

	customer_id_value = log.customer.strip()
	customer = frappe.db.get_value("Customer", {"name": customer_id_value}, "name")
	if not customer:
		customer = frappe.db.get_value("Customer", {"customer_name": customer_id_value}, "name")

	if not customer:
		log.status = "Failed"
		log.error_message = f"Customer not found for: {customer_id_value}"
		log.save(ignore_permissions=True)
		frappe.db.commit()
		return

	settings = frappe.get_doc("Mosambee Settings")

	try:
		pe_name = create_payment_entry(log, settings, customer)
		log.status = "Payment Created"
		log.payment_entry = pe_name
		log.customer_name = frappe.db.get_value("Customer", customer, "customer_name") or ""
		log.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception:
		error_trace = frappe.get_traceback()
		# Reconnect DB in case connection died (e.g. RQ job timeout)
		try:
			frappe.db.close()
		except Exception:
			pass
		frappe.connect()
		frappe.set_user("Administrator")
		try:
			frappe.log_error(error_trace, "Mosambee Payment Entry Error")
		except Exception:
			pass
		try:
			failed_log = frappe.get_doc("Mosambee Transaction Log", log_name)
			failed_log.status = "Failed"
			failed_log.error_message = error_trace[-1000:]
			failed_log.save(ignore_permissions=True)
			frappe.db.commit()
		except Exception:
			pass


def populate_log_fields(log, data, checksum_valid):
	log.transaction_id = data.get("transactionID") or data.get("transactionId") or ""
	log.transaction_date = data.get("transactionDate", "")
	log.transaction_time = data.get("transactionTime", "")
	log.transaction_amount = flt(data.get("transactionAmount", 0))
	log.transaction_status = data.get("transactionStatus", "")
	log.response_code = str(data.get("responseCode", ""))
	log.transaction_type_name = data.get("transactionTypeName", "")
	log.transaction_type_id = str(data.get("transactionTypeId", ""))
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


def get_mode_of_payment(log, settings):
	txn_type_id = str(log.transaction_type_id or "")

	if txn_type_id in ("22", "24"):
		return "UPI"
	if txn_type_id == "1":
		return "Credit Card"

	return settings.default_mode_of_payment or "Credit Card"


def validate_checksum(data, salt_value):
	transaction_id = str(data.get("transactionID") or data.get("transactionId") or "")
	merchant_id = str(data.get("merchantId", ""))
	transaction_rrn = str(data.get("transactionRRN", ""))

	raw_string = transaction_id + merchant_id + transaction_rrn + salt_value
	computed_checksum = hashlib.sha512(raw_string.encode()).hexdigest()

	received_checksum = str(data.get("checksum", ""))
	return computed_checksum.lower() == received_checksum.lower()


def create_payment_entry(log, settings, customer):
	company = settings.default_company
	paid_from = settings.default_paid_from_account
	paid_to = settings.default_paid_to_account
	mode_of_payment = get_mode_of_payment(log, settings)

	paid_from_currency = frappe.db.get_value("Account", paid_from, "account_currency")
	paid_to_currency = frappe.db.get_value("Account", paid_to, "account_currency")

	pe = frappe.new_doc("Payment Entry")
	pe.payment_type = "Receive"
	pe.party_type = "Customer"
	pe.party = customer
	pe.company = company
	pe.posting_date = frappe.utils.today()
	pe.paid_amount = log.transaction_amount
	pe.received_amount = log.transaction_amount
	pe.mode_of_payment = mode_of_payment
	pe.reference_no = log.transaction_rrn or log.transaction_id
	pe.reference_date = frappe.utils.today()
	pe.paid_from = paid_from
	pe.paid_from_account_currency = paid_from_currency
	pe.paid_to = paid_to
	pe.paid_to_account_currency = paid_to_currency
	pe.source_exchange_rate = 1
	pe.target_exchange_rate = 1
	pe.custom_mosambee_transaction_log = log.name

	pe.remarks = (
		f"Payment received via Mosambee POS Device.\n"
		f"Transaction ID: {log.transaction_id}\n"
		f"RRN: {log.transaction_rrn}\n"
		f"Card: {log.card_type} {log.transaction_card_number}\n"
		f"Card Holder: {log.card_holder_name}"
	)

	pe.flags.ignore_permissions = True
	if settings.skip_payment_entry_validation:
		pe.flags.ignore_validate = True
	pe.insert(ignore_permissions=True)

	return pe.name
