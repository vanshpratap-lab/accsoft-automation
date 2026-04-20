PROJECT: Accsoft Automation



\---



\## CURRENT STATUS



\* Phase 1 completed (Login + Navigation)



\* Phase 2 completed and FIXED (Assignment detection working correctly)



\* Phase 3.1 completed (Subject navigation stable)



\* Git workflow:



&#x20; \* main → stable

&#x20; \* dev → active development



\---



\## PHASE 1: Login + Navigation ✅



\* Open login page

\* Fill credentials

\* Detect login via URL change

\* Navigate:

&#x20; Dashboard → Academic → Assignments



\---



\## PHASE 2: Assignment Detection ✅



Goal:



\* Detect subjects with new assignments



Implementation:



\* Parse assignments table rows

\* Filter valid rows (len(cells) == 5)

\* Extract:

&#x20; subject name

&#x20; new assignment count

\* Store results in structured format (list/dict)

\* Return data for reuse in Phase 3



Output example:

Subject: Engineering Physics \& Materials → has new assignments



\---



\## PHASE 3.1: Subject Navigation ✅



Goal:



\* Open subjects with new assignments sequentially



Implementation:



\* Store row indices (not locators)

\* Re-fetch rows after navigation

\* Controlled navigation:

&#x20; Academic → Assignments (no page.go\_back)



Flow:

Assignments → Subject → Assignments → Next Subject



\---



\## NEXT TASK (CURRENT FOCUS)



Phase 3.2 → Detect assignments inside subject page



Goal:



\* Extract assignment details inside each subject:



&#x20; \* Assignment number

&#x20; \* Due date

&#x20; \* Detect download availability



\---



\## UPCOMING PHASES



Phase 3.3 → Download assignment files

Phase 3.4 → AI solve assignments

Phase 3.5 → Upload solutions



\---



\## TECH STACK



\* Python 3.14

\* Playwright (sync API)



\---



\## FILES



\* main.py → automation logic

\* requirements.txt → dependencies

\* PROJECT\_CONTEXT.md → project state



\---



\## IMPORTANT RULES



\* Do NOT modify Phase 1 logic

\* Do NOT modify Phase 2 logic

\* Do NOT modify Phase 3.1 logic

\* Only extend Phase 3 further



\---



\## GOAL



Build full automation pipeline:



Login → Detect Assignments → Open Subject → Extract Assignments → Download → AI Solve → Upload



