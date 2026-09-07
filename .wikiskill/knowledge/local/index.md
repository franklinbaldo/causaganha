# CausaGanha Wisk local state

This directory is reserved for CausaGanha-owned Wisk specializations and learned state that must survive fresh checkouts.

The managed Wisk bootstrap surface (`manifest.json`, normative specs, canonical roles and the standard profile) is created by `wisk init .` and is intentionally not versioned. Add local `SessionType`/`RunSpec` specializations here only when they express CausaGanha-specific domain requirements that should not live in Wisk core.
