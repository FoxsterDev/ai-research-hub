# Paid Module Skill Templates

Use these templates to create a new local/private paid skill pack.

## Files

- `module.json.template`: module root manifest.
- `installer.json.template`: optional commercial installer manifest.
- `pack.json.template`: paid pack manifest.
- `pack_README.md.template`: pack README.
- `routing.md.template`: first skill routing entrypoint.
- `primary_skill.md.template`: primary private skill entrypoint.
- `role.md.template`: optional paid role/brain entrypoint.
- `usage.md.template`: utility usage entrypoint.
- `review_gate.md.template`: optional paid review gate.
- `entitlements.personal_dev.json.template`: local entitlement example.
- `verify_commands.md.template`: command checklist for validation and routing.

## Token Replacement

Replace:

```text
{{MODULE_ID}}
{{MODULE_DISPLAY_NAME}}
{{MODULE_MOUNT_NAME}}
{{MODULE_VERSION}}
{{PACK_ID}}
{{PACK_DISPLAY_NAME}}
{{PACK_SLUG}}
{{LICENSE_FEATURE}}
{{CAPABILITY_ID}}
{{TRIGGER_TEXT}}
{{ROLE_FILE}}
{{SKILL_FOLDER}}
{{PRIMARY_SKILL_FILE}}
{{REVIEW_FILE}}
{{UTILITY_FILE}}
```

Example:

```text
{{MODULE_ID}} -> xcntp
{{MODULE_MOUNT_NAME}} -> XCNT-P
{{PACK_ID}} -> xcntp.game_qa_paid_skill
{{PACK_SLUG}} -> game_qa_paid_skill
{{CAPABILITY_ID}} -> xuunity.game_qa.runtime_ui_validation
```

## Expected Private Folder

```text
XCNT-P/
  module.json
  packs/
    {{PACK_SLUG}}/
      pack.json
      README.md
      role/
      skills/
        {{SKILL_FOLDER}}/
          routing.md
          {{PRIMARY_SKILL_FILE}}
      reviews/
      utilities/
```
