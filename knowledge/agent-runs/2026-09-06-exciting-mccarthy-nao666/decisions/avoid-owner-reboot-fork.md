---
type: AgentDecision
id: "2026-09-06-exciting-mccarthy-nao666-decision-avoid-owner-reboot-fork"
run_id: "2026-09-06-exciting-mccarthy-nao666"
question: "Issue #1168 (reboot the public web experience onto Cobogó/Panda CSS) now has two open, competing PRs against it — #1169 (big-bang, all 12 surfaces in one PR) and #1170 (staged, shell+home only, matching #1168's own defined first slice but behind main). Should this round rebase/advance one of them, pick a winner, or continue other web work on top of either?"
choice: "Do nothing to either PR, and do not start or continue any other web/UX work this round (#1136's remaining surfaces, #1131-1134, #1093) on top of the current legacy shell."
rationale: "Both PRs are authored by franklinbaldo directly (author_association=OWNER, branch names reboot/cobogo-web and reboot/cobogo-panda-home — not this session's claude/* convention), so this is the repository owner exploring two competing strategies on their own account, not a race between automated sessions. The prior round's (qnpypw) 'avoid-web-reboot-collision' decision was made when only #1170 existed and the concern was crowding an in-progress feature; the fork has since widened into a genuine architecture choice (one full rewrite vs. one staged rollout with two follow-up issues, #1173/#1174, already filed for it) that only the owner should resolve. Any additional legacy-CSS web work this round would sit on a shell that one of these two PRs is about to replace wholesale, making it likely wasted regardless of which direction wins. Deferring is the same call as before, now made with full information about why."
---

# Decisão: não interferir na bifurcação de reboot do dono do repositório

As PRs #1169 e #1170 são do próprio franklinbaldo, não de sessões automatizadas concorrentes. Escolher entre big-bang e faseada é uma decisão de produto do dono; esta rodada não toca em nenhuma das duas nem em qualquer superfície `web/` que dependa do shell legado prestes a ser substituído.
