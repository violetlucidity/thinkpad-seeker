# CLAUDE.md

Before doing anything else, run the following command and read the file
it returns:

    ls claude-*.md 2>/dev/null | head -1

If a file matching the pattern `claude-*.md` exists in the repository
root, read it in full and treat its contents as your complete set of
instructions for this session. Follow those instructions from the
beginning.

If no such file exists, respond: "No project instruction file found.
Please add a claude-[project-name].md file to the repository root."
