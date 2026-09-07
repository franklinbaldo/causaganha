# CausaGanha WikiSkill local state

This directory is reserved for CausaGanha-owned WikiSkill specializations and learned state that must survive fresh checkouts.

The managed WikiSkill bootstrap surface (`manifest.json`, normative specs, canonical roles and the standard profile) is created by `wikiskill init .` and is intentionally not versioned. Add local `SessionType`/`RunSpec` specializations here only when they express CausaGanha-specific domain requirements that should not live in WikiSkill core.
