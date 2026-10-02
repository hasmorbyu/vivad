VIVAD — synthetic demonstration case VV-2026-00042
==================================================

Everything in this folder is fictional. No real person, account, number or amount is used.

To reproduce the demonstration case from scratch:

1. CASES -> NEW CASE
   Title:       Security deposit deduction dispute
   Category:    Rental dispute
   Amount:      40000
   Location:    Bengaluru
   Description: Tenant seeks return of a Rs. 40,000 security deposit; landlord proposes a
                deduction for alleged damage.

2. Add the two parties (Investigation -> Case file -> Parties):
   Aarav Menon   COMPLAINANT   +91 98765 43210   Tenant
   Neel Kapoor   RESPONDENT    +91 90000 11111   Landlord

3. Add the two statements (Investigation -> Case file -> Statements):

   COMPLAINANT (Aarav Menon):
     Claim: The full Rs. 40,000 security deposit was paid on 14 Sep 2026.
     What:  Paid the full security deposit by UPI when the lease began.
     When:  14 Sep 2026
     Where: 12 Rose Apartments, Bengaluru
     Seeks: Return the deposit in full.

   RESPONDENT (Neel Kapoor):
     Claim: Only Rs. 25,000 was paid towards the deposit and Rs. 15,000 is deductible for damage.
     What:  States that less was received and that a deduction is owed for damage.
     When:  14 Sep 2026
     Where: 12 Rose Apartments, Bengaluru
     Seeks: Set off the repair cost against the deposit.

4. Upload every file in this folder as evidence (Investigation -> Evidence).

5. Run analysis. You should see the same result as the seeded case:
   - 2 claims (CL-001 supported, CL-002 unsupported)
   - 2 potential contradictions (C-001 cross-party amount mismatch, C-002 missing support)
   - 6 legal references (Transfer of Property Act s.108, Indian Contract Act s.73/74, ...)
   - the case graph with parties, claims, evidence, events, contradictions and laws

Hearings, human review and the final decision are recorded manually in the REVIEW tab.
