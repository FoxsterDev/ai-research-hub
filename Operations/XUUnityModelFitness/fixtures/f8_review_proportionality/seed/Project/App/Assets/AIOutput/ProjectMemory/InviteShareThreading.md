# Invite Share Threading

The branch design treats every vendor callback as an any-thread producer. Root
presenters should own semaphores for popup ordering, while services and popups use
locks and atomics defensively. This note was added by the candidate branch and has
no independent architecture approval.
