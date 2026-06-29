import frappe
from frappe.utils import getdate
from frappe.utils.data import flt
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
        val=frappe.db.get_value("Bank Transaction Log",{"reference_no":Reference_No},"name")
        if not val:
            doc=frappe.new_doc("Bank Transaction Log")
            doc.transaction_date=getdate(Transaction_Date)
            doc.virtual_account_no=Virtual_Account_No
            doc.reference_no=Reference_No
            doc.amount=Amount
            doc.type=Type
            doc.insert(ignore_permissions=True)
            return {"message": "Payment Successful", "stts_flg": "Y"}
        else:
            return {"message": "Payment Failed", "stts_flg": "N"}

    except Exception:
        frappe.log_error(frappe.get_traceback(), "Axis Bank Integration Payment Error")
        frappe.local.response['http_status_code'] = 500
        return {"message": "Payment Failed", "stts_flg": "N"}

#--------------------------------------------------------------------------------------------- 



