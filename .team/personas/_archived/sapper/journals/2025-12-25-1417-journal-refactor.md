    ---
    title: "💣 Refactored Journaling Exceptions"
    date: 2025-12-25
    author: "Sapper"
    emoji: "💣"
    type: journal
    ---

    ## 💣 2025-12-25 - Structured Exceptions for Journaling
    **Observation:** The  function in  was swallowing specific errors (, ) into broad  blocks and returning . This violated the "Trigger, Don't Confirm" principle by forcing the caller to handle a nullable return type and hiding the root cause of the failure.

    **Action:** I implemented a structured exception hierarchy to make these failure modes explicit.
    1.  Created a new  module.
    2.  Defined a base  and two specific exceptions:  and .
    3.  Wrote failing tests to assert that these new exceptions were raised in the appropriate scenarios.
    4.  Refactored  to catch the low-level exceptions and raise the new, context-rich domain exceptions, preserving the original stack trace with .
    5.  Corrected the function's type hint from  to , ensuring type safety.

    **Reflection:** This was a clean and successful application of my core philosophy. The resulting code is more robust and easier to debug. A potential next step would be to audit other parts of the  module for similar patterns of error swallowing. The  function, for instance, catches a generic  and wraps it in a , which could be a good target for a more specific exception.
    EOF
