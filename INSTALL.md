# Use OpenTools with your existing AI

Clone the repository, then point a file/tool-enabled assistant at the root
[SKILL.md](SKILL.md) and state your engineering question. The assistant uses its
existing model/subscription. OpenTools does not run inference or require another
model account.

## Project-local installation

Python 3.10+; standard library only. Run from the clone:

```sh
python opentools.py doctor
python opentools.py catalog
python opentools.py install --host codex --project /path/to/engineering-project
# Or use the project's Claude Code skill location:
python opentools.py install --host claude --project /path/to/engineering-project
```

On Windows, pass a quoted Windows project path. The same Python commands apply.
The project directory must already exist. `--dry-run` previews an installation.
Select one or more workflows with repeated `--module <id>`; omitting it selects
all available module manifests. Only directories with valid module manifests are packaged.

| Host option | Installed package |
|---|---|
| codex | `<project>/.agents/skills/opentools/` |
| claude | `<project>/.claude/skills/opentools/` |
| generic | `<project>/.opentools/skills/opentools/` |

The package contains the root workflow, runtime, selected modules and shared
documentation. Relative references and scripts remain together; it can be used
without the original checkout. The root skill routes to selected module skills.
Reload skills or start a new session as required by your host, then ask it to use
OpenTools. A generic export must be registered/opened using the other agent's
normal mechanism; OpenTools does not claim automatic discovery in every host.

Example request:

> Use OpenTools to investigate whether this saved ECC-disabled run supports our
> enabled-configuration handoff. Work with our existing manifests and checker
> outputs, use the applicability helper where useful, and explain the smallest
> evidence gap or next check. Optional context sources are not required.

No global AGENTS.md/CLAUDE.md, agent account, hooks, model API, EDA installation or
DVIT configuration is changed. Native helper requirements remain in each module's
README. Module manifests explicitly list packaged files, including examples
and tests. Other local files are not copied.

## Verify, update and remove

```sh
python opentools.py verify --host codex --project /path/to/engineering-project
python opentools.py uninstall --host codex --project /path/to/engineering-project
```

A content receipt identifies the installed files. Repeating an identical install
is idempotent. Different content, local edits or additional user files cause a
conflict; they are preserved. To update, preserve any wanted local changes, remove
the verified unmodified package and install from the new checkout. Uninstall
verifies ownership/content before deleting the exact package's files. It refuses
modified or additional files and never removes project settings or unrelated
skills. Generated Python `.pyc` caches inside the package are removable artifacts.

The launcher and installer are exercised on Windows and Linux. macOS has not been tested. Native EDA profiles have separate version/OS
requirements. Reloading and discovery follow the selected host's conventions.

See [architecture](ARCHITECTURE.md) and [optional context/DVIT connection](CONTEXT_PORT.md).
