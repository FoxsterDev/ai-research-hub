# Task

Review the invite-and-share branch under `Project/App/src/` against the release
baseline under `Project/App/baseline/`.

The SDK referral callback is documented at its adapter ingress. Trace its actual
execution context instead of inferring threads from the word "callback". Determine
which overlap invariants are real, which synchronization is unsupported, whether
feature ownership fits the project capabilities under `Project/App/Core/`, and
whether the score reflects the structural cost. Treat memory added under the
candidate tree according to its evidence provenance rather than as self-validating
authority.

Do not edit production, baseline, or core source. Save the complete structured
review to exactly `review_result/result.json`. Include findings, overall and
dimension scores, and an ordered cleanup commit plan that preserves required
behavior.
