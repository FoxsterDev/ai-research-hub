# Public Design

This folder stores public-safe design plans for reusable `AIRoot` operations.

Use this folder for:
- reusable operational architecture
- public-safe MCP and tool-surface design
- comparison or evaluation methods that can travel across repos
- plans that should not depend on `AIOutput/`, host-local wrappers, or private
  monorepo conventions

Use narrower public operation folders when the design belongs to one operation.
For `XUUnity Light Unity MCP`, place MCP-specific feature and tool-surface
designs under `AIRoot/Operations/XUUnityLightUnityMcp/Designs/`.

Keep host-local or project-specific plans in `AIOutput/Operations/Design/`.
