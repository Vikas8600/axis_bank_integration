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
    doc = frappe.get_doc("Bank Integration Setting")

    Acc_No = None
    auto_submit = 0
    for i in doc.bank_configuration:
        company = i.company
        cost_center = i.cost_center
        company_ba = frappe.get_doc("Bank Account", {"name": i.bank_account})
        auto_submit += i.auto_submit_of_payment_entry

        if i.has_special_character == 1:
                Acc_No = Virtual_Account_No[:-5] + i.special_character + Virtual_Account_No[-5:]

    if Acc_No and Reference_No:
        # corporate_code = Virtual_Account_No[0:4]
        customer_id = Acc_No[4:]

    else:
        customer_id = Virtual_Account_No[4:]
    

    # bank_acc_no = frappe.db.get_all("Bank Account", {"party": customer_id, "bank_account_no": Remitter_Account_No})
    # if not bank_acc_no:
    #     msg = "Invalid Remitter Account No"
    #     frappe.local.response['http_status_code'] = 404
    #     return {"message": msg, "stts_flg": "N"}

    # bank_acc = frappe.get_doc("Bank Account", {"party": customer_id, "bank_account_no": Remitter_Account_No})
    cus = frappe.get_doc("Customer", customer_id)

    party_type = "Customer"
    party = cus.name
    date = Transaction_Date
    party_details = get_party_details(company, party_type, party, date, cost_center)

    bank_account = company_ba.name
    com_acc_details = get_bank_account_details(bank_account)

    if Type == "N":
        types = "NEFT"
    elif Type == "R":
        types = "RTGS"
    elif Type == "I":
        types = "IMPS"
    else:
        types = Type

    try:

        cus = frappe.get_doc("Customer", customer_id)
        # bank_acc = frappe.get_doc("Bank Account", {"party": customer_id, "bank_account_no": Remitter_Account_No})
        co_bank_acc = frappe.db.get_value("Bank Account", {"name": company_ba.name}, ["name"])
        ref_no = types + "/" + Reference_No
        # if cus and bank_acc:
        if cus:
            new_pay_ent = frappe.new_doc("Payment Entry")
            new_pay_ent.payment_type = "Receive"
            new_pay_ent.party_type = "Customer"
            new_pay_ent.posting_date = Transaction_Date
            # new_pay_ent.mode_of_payment = types
            new_pay_ent.paid_amount = flt(Amount)
            new_pay_ent.received_amount = flt(Amount)
            new_pay_ent.bank_account = co_bank_acc
            new_pay_ent.party = cus.name
            new_pay_ent.party_name = party_details.get("party_name")
            # new_pay_ent.party_bank_account = bank_acc.name
            new_pay_ent.paid_from = party_details.get("party_account")
            new_pay_ent.paid_from_account_currency = party_details.get("party_account_currency")
            new_pay_ent.paid_to_account_currency = party_details.get("party_account_currency")
            new_pay_ent.party_balance = party_details.get("party_balance")
            new_pay_ent.paid_from_account_balance = party_details.get("account_balance")
            new_pay_ent.paid_to = com_acc_details.get("account")
            new_pay_ent.reference_no = ref_no
            new_pay_ent.reference_date = Transaction_Date
            new_pay_ent.source_exchange_rate = 1
            new_pay_ent.target_exchange_rate = 1
            
            pay_ent = frappe.db.get_value("Payment Entry", {"reference_no": ref_no},"name")
            if not pay_ent:
                if auto_submit == 1:
                    new_pay_ent.submit()
                    return {"message": "Payment Successful", "stts_flg": "Y"}
                else:
                    new_pay_ent.save(ignore_permissions=True)
                    return {"message": "Payment Successful", "stts_flg": "Y"}

            else:
                # frappe.local.response['http_status_code'] = 409
                return {"message": "Duplicate Entry", "stts_flg": "N"}

    except:
        traceback = frappe.get_traceback()
        frappe.log_error(title = 'Axis Bank Integration payment Error',message=traceback)

#--------------------------------------------------------------------------------------------- 