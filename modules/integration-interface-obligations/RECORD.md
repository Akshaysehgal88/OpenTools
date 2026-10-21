# Integration interface review

- Interface/configuration/mode/revision:
- Native connectivity export and exact source/tool basis:
- Selected endpoint population and missing/unsupported connections:

| Obligation | Producer offers | Consumer requires | Native/source evidence | Conclusion or missing evidence |
|---|---|---|---|---|
| Admission/receipt | | | | |
| Completion/side effect | | | | |
| Cancellation and late response | | | | |
| Request/event persistence | | | | |
| Clock/reset and outstanding state | | | | |

Keep event meaning separate from its signal name. An accepted request may still
be pending; cancellation may be best effort after commit. Supply source references
for these meanings and each consumer assumption. A matching port export alone
cannot fill this table.

- Original native findings/status:
- Independent engineering interpretation:
- Unsupported or contradictory premise:
- Useful next check, or why existing evidence is sufficient:
- Existing review owner/decision reference, if applicable:
