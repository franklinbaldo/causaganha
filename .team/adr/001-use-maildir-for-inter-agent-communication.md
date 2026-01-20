# 001: Use Maildir for Inter-Agent Communication

- **Status**: Accepted
- **Date**: 2024-07-30

## Context

The various AI personas within the Egregora system need a reliable method for asynchronous communication. This mechanism must be simple to understand, easy to debug, and work well with our Git-based workflow. We considered several options, including a database-backed message queue, but these were deemed overly complex for our current needs.

## Decision

We have decided to use the Maildir format for inter-agent communication. Each persona is assigned a directory within `.team/mail/`, which is structured according to the Maildir specification. Messages are stored as individual, RFC 822-compliant text files. This approach allows for robust, lock-free communication between personas.

## Consequences

### Positive:
- **Simplicity**: The file-based nature of Maildir makes it easy to inspect and debug communications. We can simply look at the files in the directory to see the state of the system.
- **Git-Friendly**: Since messages are just text files, they can be easily tracked in version control, providing a clear history of all communications.
- **Robustness**: Maildir is a well-established and battle-tested standard that is resistant to data loss.
- **No External Dependencies**: This approach does not require any external services like a database or message broker, which simplifies our architecture and deployment.

### Negative:
- **Performance**: At a very high message volume, a dedicated message queue might be more performant. However, this is not a concern for our current use case.
- **Custom Tooling**: We have had to develop custom tooling (`repo/mail_cli.py` and `repo/mail.py`) to interact with the mailboxes. This is a small price to pay for the simplicity and robustness of the system.
