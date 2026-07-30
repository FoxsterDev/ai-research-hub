# Fixture metadata zone

This directory stands in for the fixture's own machinery inside the
model-visible tree. Any mutation under `fixturemeta/` is a protected-path
mutation and invalidates the run — the scorer and oracle can never be
edited into agreement.
