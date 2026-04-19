PROJECT: Accsoft Automation



\---



\## CURRENT STATUS



\* Phase 1 completed (Login + Navigation)



\* Phase 2 completed (Assignment detection — needs minor fix)



\* Phase 3.1 completed (Subject navigation working)



\* Git branching introduced:



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



\## PHASE 2: Assignment Detection ⚠️ (Needs Fix)



Goal:



\* Detect subjects with new assignments



Current Issue:



\* Phase 2 sometimes prints:

&#x20; "No subjects with new assignments found"

\* But Phase 3 correctly detects subjects



Conclusion:



\* Phase 2 extraction logic OR filtering condition is inconsistent



\---



\## PHASE 3.1: Subject Navigation ✅



Goal:



\* Click subjects with new assignments one-by-one



Implemented:



\* Store row indices (not locators)

\* Re-fetch rows after navigation

\* Controlled navigation:

&#x20; Academic → Assignments (no page.go\_back)



Flow:

Assignments → Subject → Assignments → Next Subject



\---



\## CURRENT TASK



Fix Phase 2 inconsistency



\---



\## NEXT PHASE



Phase 3.2 → Detect assignments inside subject page



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

\* Do NOT modify Phase 3.1 logic

\* Only fix Phase 2 logic now



\---



\## GOAL



Build a fully automated system:



Login → Detect Assignments → Open Subject → Extract Assignments → Download → AI Solve → Upload



