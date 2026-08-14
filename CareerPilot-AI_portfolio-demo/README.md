# lumooi Portfolio Demo

This is Liu Zefei's editable, sanitized portfolio edition of the personal CareerPilot/lumooi application.

The Demo keeps the real name, public education, public employers, project directions and all 56 Experience Bank assets. It uses a detached static snapshot and an independent local database, so later changes in the personal version are never copied automatically.

## Privacy boundary

- The expanded asset view does not expose AI-usage notes, internal interview-memory notes, or parent-experience rules.
- Colleague identities, private contacts, internal files, exact sensitive business data and unverified internal judgments are excluded or generalized.
- Job application companies are labeled `Job 01` through `Job 09`; role titles and JD content remain, while application stages and dates are fictional Demo data.
- The Demo never opens or imports the private CareerPilot database.
- The only runtime database is generated locally as `data/portfolio_demo.db`.

## Run locally

```bash
python -m streamlit run app.py --server.port 8503
```

Editing remains enabled. To reset the public Demo content, delete only `data/portfolio_demo.db` and restart the app.

Before publishing, run `python privacy_scan.py`. A non-zero result must be reviewed.
