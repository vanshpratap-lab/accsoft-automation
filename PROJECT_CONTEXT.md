PROJECT\_CONTEXT.md



\# PROJECT: Accsoft Automation



\---



\## CURRENT STATUS



✔ Phase 1 completed (Login + Navigation stable)  

✔ Phase 2 completed and FIXED (Assignment detection accurate)  

✔ Phase 3.1 completed (Subject navigation stable and sequential)  

✔ Phase 3.2 completed (Assignment extraction working)



Git workflow:



\- main → stable production code

\- dev → active development branch



\---



\## PHASE 1: Login + Navigation ✅



\### Goal:

Automate login and reach assignments section



\### Implementation:



\- Open login page

\- Fill credentials

\- Submit form

\- Wait for successful login (URL change detection)

\- Navigate:

&#x20; Dashboard → Academic → Assignments



\### Status:

✔ Stable  

✔ No changes required



\---



\## PHASE 2: Assignment Detection ✅



\### Goal:

Identify subjects with new assignments



\### Implementation:



\- Locate assignments table

\- Filter valid rows (len(cells) == 5)

\- Extract:

&#x20; - Subject name

&#x20; - New assignment count

\- Group duplicate subjects

\- Return structured list of subjects with new assignments



\### Output Example:

Subject: Engineering Physics \& Materials → has new assignments



\### Status:

✔ Fully working  

✔ Bug-fixed (correct row parsing)



\---



\## PHASE 3.1: Subject Navigation ✅



\### Goal:

Open each subject with new assignments sequentially



\### Implementation:



\- Store row indices (NOT locators)

\- Re-fetch rows after each navigation

\- Click subject → open → return safely

\- Avoid `go\_back()` (use controlled navigation)



\### Flow:



Assignments → Subject → Assignments → Next Subject



\### Status:

✔ Stable  

✔ No navigation issues



\---



\## PHASE 3.2: Assignment Extraction ✅



\### Goal:

Extract assignment data from subject page



\### Implementation:



\- Navigate to subject page (Assignment.aspx)

\- Locate assignment container

\- Extract rows using:

&#x20; tr.GreenPage2

\- Extract per row:

&#x20; - Assignment Number (index 2)

&#x20; - Due Date (index 3)

&#x20; - Status (button-based detection)



\### Logic:



\- Skip invalid rows

\- Use index-based extraction (robust against layout issues)

\- Handle dynamic DOM (non-standard table structure)



\### Output Example:



Assignment 05 | Due: 20-Apr-2026 | Status: Upload  

Assignment 04 | Due: 13-Apr-2026 | Status: Date Expired  



\### Status:



✔ Assignment extraction working  

✔ Multi-subject extraction working  

⚠ Status detection partially working (buttons need better parsing — improvement pending)



\---



\## NEXT TASK (CURRENT FOCUS)



\## 🚀 PHASE 3.3 → Download Assignments



\### Goal:



\- Automatically click "Download" button

\- Save assignment files locally

\- Organize by subject



\---



\## UPCOMING PHASES



\### Phase 3.4 → AI Solve Assignments



\- Process downloaded files

\- Generate answers using AI



\### Phase 3.5 → Upload Solutions



\- Upload solved assignments automatically



\---



\## TECH STACK



\- Python 3.14

\- Playwright (sync API)



\---



\## FILES



\- main.py → core automation logic

\- requirements.txt → dependencies

\- PROJECT\_CONTEXT.md → project state



\---



\## IMPORTANT RULES



\- DO NOT modify Phase 1 logic

\- DO NOT modify Phase 2 logic

\- DO NOT modify Phase 3.1 logic

\- DO NOT break working extraction logic in Phase 3.2

\- Only extend functionality forward



\---



\## FINAL GOAL



Build full automation pipeline:



Login → Detect Subjects → Open Subject → Extract Assignments → Download → AI Solve → Upload

