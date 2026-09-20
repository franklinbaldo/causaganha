# CausaGanha Wisk local state

This directory is reserved for CausaGanha-owned Wisk specializations and learned state that must survive fresh checkouts.

The managed Wisk bootstrap surface (`manifest.json`, normative specs, canonical roles and the standard profile) is created by `wisk init .` and is intentionally not versioned. Add local `SessionType`/`RunSpec` specializations here only when they express CausaGanha-specific domain requirements that should not live in Wisk core.


## Consumer-owned policy

CausaGanha-specific Wisk state should be material and reusable, not ceremonial. Prefer OKF consumed through the repository's current compatible `okf-parser` for durable operational state. Do not add a local tracking format when OKF already represents the knowledge.

A repeated external blocker belongs here or in another appropriate durable OKF object with an explicit reactivation condition; it should not generate a new closeout PR on every run.

Round completion by itself is not consumer knowledge. Do not create local SessionType/RunSpec specialization whose main effect is to force a documentation-only PR after substantive work has already landed.
