# AivaCare Roadshow Demo Script (about 8 minutes)

All data is synthetic. Open four browser tabs/devices before you start:

| Screen | URL / device | Sign in as |
|---|---|---|
| A. Patient phone | AivaCare Android app (or the patient web portal on a phone) | John Miller |
| B. Clinician dashboard | `<web-url>/` → Dr. Anika Patel | Hepatologist |
| C. Presenter controls | `<web-url>/` → Demo Admin (keep out of view) | Admin |
| D. Patient web portal | `<web-url>/` → John Miller | Patient (for the upload step) |

**Before the audience arrives:**
1. On C, click **Reset**. Check that the status chips show "FHIR server: up" and "Claude API: configured".
2. On B, confirm the alert queue shows 2 high and 3 medium alerts, all marked "AI review ready".

---

## 1. The problem (30 seconds)
"John is 48 and has fatty liver disease. He sees his hepatologist every 3 months. His labs, records and Apple Watch data sit in separate systems, and between visits nobody is watching the trend."

## 2. John's day, on his phone (1.5 minutes), on screen A
- Home: ALT trending back up (44 → 52 → 67), weight creeping up, steps falling. Point out that labs come from the clinic's EHR and the daily metrics from his watch, all in one FHIR record.
- Assistant: tap **"Why is my ALT high and what should I eat?"**
  - Watch the tool chips: it *checked your trend data* and *searched approved guidance*.
  - The answer quotes his exact values and cites **[S1] LiverWell Nutrition Guide v3.1**.
  - Key message: "Numbers come from his record, advice comes only from clinician-approved content, with sources."

## 3. Medical report upload (1 minute), on screen D
- Go to Upload, choose `sample-labs/john-miller-liver-panel.pdf`, then **Read report**.
- Claude extracts ALT, AST, GGT, albumin, platelets and HbA1c. Glucose shows as "not tracked", and units and ranges are validated.
- John confirms the values. They are saved to FHIR with provenance that links them to the document.

## 4. The deterioration (1 minute), on screens C then B
- On C, click **Inject deteriorating labs** ("The lab feed just sent new results").
- On B, a **High** alert appears live: *FIB-4 above 2.67*.
  - Point out that the **deterministic rules engine** raised it, not the AI.
  - "AI reviewing…" changes to "AI review ready" within seconds.

## 5. Clinician review and approval (2 minutes), on screen B
- Open John's alert, which goes to Patient 360. Show:
  - **Rule evidence**: FIB-4 2.87 against the 2.67 threshold, and ALT doubled from his 44 baseline.
  - **Copilot review**: the headline, bullets with exact values, and citations to the LiverWell fibrosis pathway [P#].
  - **Proposed actions**, a draft only: untick one, add "Repeat liver panel in 4 weeks".
- In the Copilot panel ask **"What changed in the last 90 days?"**. It answers using governed MCP tools.
- Click **Approve & notify patient**. This is the human-in-the-loop step: nothing changed until a physician approved.

## 6. Closing the loop (30 seconds), on screen A
- Updates: John now has a plain-language follow-up message from his care team, and his care plan shows the new actions.

## 7. Safety (1 minute), on screen A
- In the Assistant, type **"My eyes look yellow today"**.
- The answer comes back instantly with urgent-care instructions. The **red-flag guardrail bypassed the AI**, and a high alert appears on B.
- Optionally, show **Rules & audit** on B: the versioned rule catalog and the full audit trail.

## Close
"Rules decide, AI explains, physicians approve. FHIR keeps it interoperable, and MCP-governed tools keep it secure."

---

### If something goes wrong
| Problem | Fix |
|---|---|
| The phone can't connect | Use the patient web portal on the phone's browser (same URL), or on the laptop |
| AI is slow or unavailable | Alerts, rules, approvals and the red-flag path keep working; reviews fall back to the rule template |
| The data is in a bad state | Click Reset on C (about 15-30 seconds) |
| The cloud is down | Run `docker compose up -d` in `infra/` on the laptop; the web app is on http://localhost:3710 |
