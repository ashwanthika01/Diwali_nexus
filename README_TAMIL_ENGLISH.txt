# VIP NEXUS Diwali Fund — working web-app starter

## Included
- Customer registration and login (passwords hashed)
- Admin login and admin dashboard
- Add/deactivate savings-plan display entries
- Membership status review
- Monthly collection schedule created when a member selects a plan
- Admin can record a manual collection reference and mark a row paid
- Responsive pages for mobile and desktop
- SQLite database for a local prototype

## Run locally on Windows
1. Install Python 3.10 or newer from python.org.
2. Extract this ZIP into a folder.
3. Open Command Prompt in that folder.
4. Run:
   `py -m venv .venv`
   `.venv\Scripts\activate`
   `py -m pip install -r requirements.txt`
5. Set the admin credentials in the same Command Prompt:
   `set SECRET_KEY=put-a-long-random-secret-here`
   `set ADMIN_MOBILE=9876543210`
   `set ADMIN_PASSWORD=put-a-unique-password-here`
6. Start the website:
   `py app.py`
7. Open `http://127.0.0.1:5000` in your browser.
8. Admin login: use the mobile and password set in step 5. Customer accounts can register through the site.

For PowerShell, use `$env:SECRET_KEY="..."`, `$env:ADMIN_MOBILE="9876543210"`, and `$env:ADMIN_PASSWORD="..."` before `py app.py`.

## Demo vs production — important
This is a functional starter application, not a production-ready financial service.
- Local demo: real registration/login on your own computer, SQLite records, plans, membership status and manual collection bookkeeping.
- Not implemented: payment gateway, automated bank reconciliation, SMS/WhatsApp OTP, password reset, email receipts, multi-admin permissions, audit trail, automated backups, CSRF protection, rate limiting, deployment hardening, privacy/consent workflow, or a legally compliant chit auction/prize/payout process.
- Marking a collection “paid” is only a manual record; it does not verify money reached a bank account.
- Do not publish with default secrets, and do not enter real financial/customer data until a qualified developer has hardened and reviewed the app.
- Free hosting may sleep, impose limits, or erase local files. SQLite needs a persistent disk; otherwise records may disappear on redeploy/restart. A managed database may be required.

## Payment gateway plan (not connected)
1. Complete legal review and obtain applicable approvals before inviting subscriptions/accepting chit contributions.
2. Open a merchant account with a supported provider (for example Razorpay or Cashfree) under the legally appropriate business/entity name.
3. Use hosted checkout/UPI options; never store card numbers, CVV, UPI PIN, or banking passwords.
4. Create server-side payment orders and verify signed webhook signatures on the server.
5. Update a collection to paid only after verified successful payment and reconciliation; store provider reference, amount, currency, timestamp and status.
6. Add refund, failed-payment, duplicate-webhook, dispute and reconciliation handling.
7. Use HTTPS, secret manager/environment variables, logs without sensitive data, backups and access controls.
No payment keys or live payment functions are included in this starter.

## India / Tamil Nadu compliance checklist — get professional advice
This is a technical checklist, not legal advice:
- Ask a Tamil Nadu chit-fund lawyer / Registrar of Chits whether the proposed model legally constitutes a “chit” under the Chit Funds Act, 1982, or falls under another regulated category.
- Section 4 of the Act states that a chit may not be commenced/conducted without prior State Government sanction (or empowered officer's sanction) and registration in the state, where applicable.
- Section 5 addresses notices/prospectuses inviting subscriptions and particulars of prior sanction.
- Review Tamil Nadu Chit Funds Rules, 1984 and current amendments, prescribed forms, fees, filing and record-keeping requirements with the Registrar.
- Confirm entity/foreman eligibility, written chit agreement, subscriber disclosures, security/deposit requirements, books/records, periodic filings, auction/prize process and dispute handling, as applicable to your exact model.
- Do not advertise guaranteed returns or accept money before professional confirmation of the legal route and required approvals.
- Check applicable KYC/AML, tax/GST, consumer-protection, data-protection and payment-provider requirements with qualified professionals.
Official starting points:
- India Code, Chit Funds Act, 1982: https://www.indiacode.nic.in/indiacode/handle/123456789/1797
- Tamil Nadu Chit Funds Rules, 1984 (published on India Code): https://upload.indiacode.nic.in/showfile?actid=AC_TN_85_691_00005_00005_1554107083825&filename=tamil_nadu_chit_fund_rules_1984.pdf&type=rule

## Data warning
This starter stores passwords as hashes, but it has not undergone security testing. Treat it as a development demo until professional review is completed.
