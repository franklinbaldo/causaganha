---
id: 20251230-180629-refactor-response-to-dict
status: todo
title: "Refactor `_response_to_dict` in google_batch.py for Clarity"
created_at: "2025-12-30T18:06:35Z"
target_module: "src/egregora/llm/providers/google_batch.py"
assigned_persona: "artisan"
---

## Description

The `_response_to_dict` method in `src/egregora/llm/providers/google_batch.py` is overly complex and can be simplified to improve readability and maintainability.

## Context

The current implementation of `_response_to_dict` involves manually building a dictionary from a response object, with multiple `hasattr` checks. This can be streamlined using a more direct conversion approach, reducing boilerplate and making the logic easier to follow.

## Task

Refactor the `_response_to_dict` method as identified by the `TODO: [Taskmaster]` annotation. The goal is to make the method more concise and robust.
