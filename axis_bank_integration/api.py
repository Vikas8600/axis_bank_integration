from pickle import NONE
from re import S
from frappe.utils.data import flt
from lib2to3.pgen2.token import BACKQUOTE
from logging import exception
from xml.dom import ValidationErr
import frappe
from erpnext.accounts.doctype.payment_entry.payment_entry import get_party_details
from erpnext.accounts.doctype.bank_account.bank_account import get_bank_account_details


# -------------------------validation for Corporate ID---------------------------------------

@frappe.whitelist(allow_guest=True)
def validate_corporate_id(Transaction_Date, Account_Number, Client_Code, Virtual_Account_No, Reference_No, Amount, Type):
    try:
        Acc_No = None
        bis = frappe.get_doc("Bank Integration Setting")
        for val in bis.bank_configuration:
            if val.has_special_character == 1:
                Acc_No = Virtual_Account_No[:-5] + val.special_character + Virtual_Account_No[-5:]
       
        if Acc_No:
            corporate_code = Acc_No[0:4]
            customer_id = Acc_No[4:]
        else:
            corporate_code = Virtual_Account_No[0:4]
            customer_id = Virtual_Account_No[4:]

        cus_doc = frappe.db.get_value("Customer", {"name": customer_id}, ["name"])
        if not cus_doc:
                frappe.local.response['http_status_code'] = 404
                return {"message": "Invalid Virtual Account no", "stts_flg": "N"}

        for value in bis.bank_configuration:
            if str(value.corporate_bank_code) != str(corporate_code):
                frappe.local.response['http_status_code'] = 404
                return {"message": "Invalid Virtual Account no", "stts_flg": "N"}

        else:
            return {"message": "Validated Successfully", "stts_flg": "Y"}

    except:
        traceback = frappe.get_traceback()
        frappe.log_error(title = 'Axis Bank Integration validation Error',message=traceback)

# -----------------------Payment API-----------------------------------------------------------

@frappe.whitelist(allow_guest=True)
def payment_process_from_bank(Transaction_Date, Client_Code, Virtual_Account_No, Reference_No, Amount, Type, Remitter_IFSC, Remitter_Name, Remitting_Bank_Branch, Remitter_Account_No):
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
            payment_entry.submit()
        else:
            payment_entry.insert(ignore_permissions=True)

        return {"message": "Payment Successful", "stts_flg": "Y"}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Axis Bank Integration Payment Error")
        frappe.local.response['http_status_code'] = 500
        return {"message": "Payment Failed", "stts_flg": "N"}

#--------------------------------------------------------------------------------------------- 
