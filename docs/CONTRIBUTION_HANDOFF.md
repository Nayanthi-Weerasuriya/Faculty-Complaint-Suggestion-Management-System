# Two-member contribution and GitHub handoff

## What the repository actually contains

The local repository already has four commits on main. The latest inspected commit is e0c0c92. Core architecture, tests and UI work are already represented in that history; this is not an empty repository. No GitHub remote is configured. Many final improvements are still uncommitted. Do not delete .git, reset the existing commits or pretend the finished source was developed independently on two branches.

Both members can own different modules and commit on different branches. Uploading existing files records integration; it does not establish who originally wrote them. Since you wrote the current code, retain that authorship. Your friend can genuinely review, test, explain, document and improve her assigned modules; the remaining audit findings provide real implementation work. Check the course's individual-contribution expectations with the instructor: the supplied proposal does not specify commit-count-based marks or guarantee credit for uploading files.

## Suggested functional ownership

| Group | Responsibility | Exact scope |
| --- | --- | --- |
| Shared foundation (you/integration owner) | Project setup and contracts both parts depend on | Root setup/docs, config, all models/migrations/app/package registration, common admin configuration, category definitions, shared case validators/permissions/report filter form. |
| Member A - you | Access, reporting-user experience and core operations | accounts views/forms/backends/verification/URLs/tests; authorities views/forms/URLs; cases views/forms/URLs/tests; demo seeding; templates/accounts, templates/cases, templates/authorities; templates/base.html, templates/landing.html; static CSS. |
| Member B - friend's responsibility after actual review/work | Monitoring, communications and operational assurance | dashboard/views.py, dashboard/urls.py, dashboard/tests.py; templates/dashboard; notifications/views.py, notifications/utils.py, notifications/management; templates/notifications; audit/utils.py; cases/management/commands/backup_portal.py; integration tests in cases/test_workflows.py. |

The CSV inventory lists each current file and one of these groups. The database schema is shared deliberately: migration dependencies make it unsafe to divide the Django apps into two completely isolated runnable halves. A single file may involve both people's real work; use separate commits for separate changes rather than claiming whole-file ownership proves authorship.

## Recommended route: preserve the working baseline, then make real branch contributions

1. Save a separate backup of the current project. Keep local database/uploads outside Git.
2. You commit the completed, validated existing snapshot under your own identity, including the cleanup deletions. This accurately records the work already completed. A complete shared baseline is normal; both members do not need to contribute the original scaffold.
3. Push that baseline to the chosen GitHub repository and give your friend collaborator access.
4. You create codex/member-a-core for any further core/UI work you actually perform.
5. Your friend clones the complete project and creates codex/member-b-reporting. She can implement the dynamic chart percentages, coordinator date inputs, consistent pending-authority reporting or admin-workflow test coverage listed in REQUIREMENTS_AUDIT.md. She commits only work she really performs and can explain.
6. Each opens a pull request; the other reviews it. Test and merge to main. With sequential merges, the second author updates from main before completing integration.

This produces a complete runnable base and meaningful evidence of individual contribution. Equal file counts or equal commit counts are not a substitute for actual contribution.

Commands after the baseline is safely recorded and a remote URL is configured:

```powershell
# Your working copy
 git switch main
 git switch -c codex/member-a-core
# Edit/review your actual changes, then stage only those files.
 git diff
 git add -- accounts cases authorities templates static
 git diff --cached
 git commit -m "Describe the actual core change"
 git push -u origin codex/member-a-core
```

Your friend runs in her own clone:

```powershell
 git switch main
 git pull --ff-only
 git switch -c codex/member-b-reporting
# Implement/review her actual change, run checks, then stage that work.
 git diff
 git add -- dashboard notifications audit templates/dashboard templates/notifications cases/test_workflows.py cases/management/commands/backup_portal.py
 git diff --cached
 git commit -m "Describe the actual reporting or testing change"
 git push -u origin codex/member-b-reporting
```

Do not run a commit command with no real staged changes simply to create contribution history. Use the real author and real work description in every message. Add co-author credit only for actual collaboration.

## If you specifically want to assemble the existing finished files in module batches

This is technically possible, but it is a staged integration/import plan, not a reconstruction of two people's development. Preserve original authorship and describe the imports honestly.

1. Preserve a complete copy of the current final files first. Existing tracked deletions are part of that final copy's change list.
2. Commit the shared-foundation files on main. Use the Foundation group in the CSV; it contains final shared models/configuration, not merely empty scaffolding. This intermediate milestone is not the final ready-to-demo application.
3. Create codex/member-a-core. Add the Member A files from the validated final copy and commit them as your integration of completed core/access/UI work. Merge this branch to main first.
4. Your friend clones the updated main and creates codex/member-b-reporting from that updated base. Give her the Member B files, relevant shared foundation contracts and audit report. The safest handoff is access to the complete final snapshot as reference, with commits restricted to her agreed group.
5. She reviews/integrates those files. If committing unchanged code authored by you, preserve you as Git author and herself as committer; do not describe it as new code she developed. Git's commit --author option supports this distinction, using your actual name and email. She can make separate commits under her own authorship for real subsequent fixes, tests and documentation.
6. Merge the second branch and validate the fully integrated result. Some templates/routes refer across groups, so intermediate partial imports may not render every role page. Do not claim each partial batch passed the final suite. Compare the integrated tree with the saved final copy, then run the checks below.

The two branches should therefore be **sequential**, not two disconnected half-projects developed from unrelated folders. Both get merged into the same main branch. Do not create independent repositories and copy them on top of each other, duplicate migrations, or randomly divide shared files.

## What to send your friend

- Access to the complete project source at the agreed baseline, plus the Member B files identified in docs/FILE_INVENTORY.csv.
- REQUIREMENTS_AUDIT.md, this guide and the setup instructions in README.md.
- A short list of real work she will complete, such as fixing the reporting percentages and adding their tests.
- The required Python version/dependencies and demo seed command; she creates her own virtual environment and local database.
- No .env/secrets, real user database, uploaded evidence, your virtual environment or your .git folder when sending a plain file archive. When using Git, she should clone the repository rather than receive a copied .git directory.

## Integration and final verification

```powershell
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Use a clean clone to verify the committed state, not a working folder that still contains somebody else's uncommitted files. Run seed_data only against disposable development data. Demonstrate submission, assignment, progress, resolution notification, closure, management reporting and permissions together.

## Before the first GitHub push

- Create the intended GitHub repository and configure origin with its actual URL; no remote exists yet.
- Review git status and git diff --cached. Use targeted staging; do not accidentally include db.sqlite3, venv, media evidence, backups or credentials.
- Include all migrations and the package __init__.py files. Empty package initializers are necessary Python/Django structure, not rubbish.
- Record the scaffold deletions already present: audit/tests.py, audit/views.py, authorities/tests.py, categories/tests.py, categories/views.py, dashboard/admin.py, dashboard/models.py and notifications/tests.py. Use git add -u on the appropriate reviewed paths so removed tracked files stay removed.
- No branches/commits/pushes were made by the final audit. The branch names above are a proposed plan, not existing remote branches.
