# Coding rules

- All program lines are in English: comments and all names. Texts for users of the application
  are written in English in the code and translated through the language catalogues (see
  architecture, Languages).
- Commit messages are in English.
- There are no history comments. What came before is in the version history.
- A comment describes how a solution works, never external reasons.
- A program file has at most 150 to 200 lines of code, not counting comments. Files with uniformly
  repeated content, such as language catalogues, are the exception.
- Formatting for humans: one statement per line where possible.
- Before the first release there are no migration functions in the program. Necessary migrations
  run externally with separate tools.
