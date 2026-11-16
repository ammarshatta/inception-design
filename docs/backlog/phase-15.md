# Phase 15 stories

## P15-01 · Online payments & reminders · Must

**Role:** Client  
**Story:** As a client, I want to pay a due payment online by card or mobile wallet, so that I pay without visiting the office.

**Acceptance criteria**

1. Given a due milestone and the gateway sandbox, when I press ادفع دلوقتي and complete payment, then a Payment Entry is created automatically and the milestone shows Paid.

## P15-02 · Online payments & reminders · Must

**Role:** Accountant  
**Story:** As an accountant, I want gateway notifications verified and never duplicated, so that the books are accurate.

**Acceptance criteria**

1. Given a webhook with an invalid signature, when it arrives, then it is rejected and logged.
2. Given the same successful webhook twice, when both arrive, then only one Payment Entry exists.
3. Given a missed webhook, when the 15-minute check runs, then the payment is reconciled.

## P15-03 · Online payments & reminders · Must

**Role:** Client  
**Story:** As a client, I want to upload a bank transfer or InstaPay receipt, so that I can pay without card fees.

**Acceptance criteria**

1. Given a due milestone, when I upload a transfer receipt, then the accountant is notified and confirming it creates the Payment Entry.

## P15-04 · Online payments & reminders · Must

**Role:** Client  
**Story:** As a client, I want an Arabic receipt for every payment, so that I have proof of payment.

**Acceptance criteria**

1. Given a confirmed payment, when it is recorded, then I receive an Arabic PDF receipt by email and in the portal.

## P15-05 · Online payments & reminders · Should

**Role:** Client  
**Story:** As a client, I want polite reminders before and after due dates, so that I pay on time.

**Acceptance criteria**

1. Given a milestone due on day 10, when 30 days are simulated, then I get reminders on days 7, 10, 17 and 24 and no others.

## P15-06 · Online payments & reminders · Should

**Role:** Accounts Manager  
**Story:** As an accounts manager, I want to refund a payment with an audit note, so that mistakes are fixed properly.

**Acceptance criteria**

1. Given a gateway payment, when I refund it as Accounts Manager, then the gateway refund is requested and a reversing entry with my note is created.
2. Given a user without Accounts Manager, when they try to refund, then the action is not available.
