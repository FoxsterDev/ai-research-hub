# Public Design Rules

Use the design layer with a strict split:

- cross-cutting public designs -> `AIRoot/Design/`
- operation-specific public designs -> `AIRoot/Operations/<Operation>/Designs/`
- host-local or private designs -> `AIOutput/Operations/Design/`

Use `AIRoot/Design/` for:
- reusable public architecture plans
- protocol design that spans more than one operation
- topology, automation, and policy models that should travel across repos

Do not put host-local workflow plans, private operational wrappers, or
project-specific implementation notes here.

If a design is only about one public operation, keep it under that operation's
own `Designs/` folder instead of placing it here.
