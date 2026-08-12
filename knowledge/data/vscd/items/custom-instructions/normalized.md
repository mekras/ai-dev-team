# Use custom instructions in VS Code

Use custom instructions in VS Code
💻 Join VS Code Live at MS Build on June 3.
Dismiss this update
Copy as Markdown
Copy as Markdown
View as Markdown
Try this
Generate instructions
Set up your project for AI with `/init` to generate custom instructions tailored to your project.
Open in VS Code
Stable
Insiders
Use custom instructions in VS Code
Custom instructions enable you to define common guidelines and rules that automatically influence how AI generates code and handles other development tasks. Instead of manually including context in every chat prompt, specify custom instructions in a Markdown file to ensure consistent AI responses that align with your coding practices and project requirements.
You can configure custom instructions to apply automatically to all chat requests or to specific files only. Alternatively, you can manually attach custom instructions to a specific chat prompt.
Tip
Use the
Agent Customizations editor
(Preview) to discover, create, and manage all your agent customizations in one place. Run
Chat: Open Customizations
from the Command Palette.
Note
Custom instructions are not taken into account for
inline suggestions
as you type in the editor.
Types of instruction files
VS Code supports two categories of custom instructions. If you have multiple instruction files in your project, VS Code combines and adds them to the chat context, no specific order is guaranteed.
Always-on instructions
Always-on instructions are automatically included in every chat request. Use them for project-wide coding standards, architecture decisions, and conventions that apply to all code.
A single
.github/copilot-instructions.md
file
Automatically applies to all chat requests in the workspace
Stored within the workspace
One or more
AGENTS.md
files
Useful if you work with multiple AI agents in your workspace
Automatically applies to all chat requests in the workspace or to specific subfolders (experimental)
Stored in the root of the workspace or in subfolders (experimental)
Organization-level instructions
Share instructions across multiple workspaces and repositories within a GitHub organization
Defined at the GitHub organization level
CLAUDE.md
file
For compatibility with Claude Code and other Claude-based tools
Stored in the workspace root,
.claude
folder, or user home directory
File-based instructions
File-based instructions are applied when files that the agent is working on match a specified pattern or if the description matches the current task. Use file-based instructions for language-specific conventions, framework patterns, or rules that only apply to certain parts of your codebase.
One or more
.instructions.md
files
Conditionally apply instructions based on file type or location by using glob patterns
Stored in the workspace or user profile
To reference specific context in your instructions, such as files or URLs, you can use Markdown links.
Tip
Which approach should you use?
Start with a single
.github/copilot-instructions.md
file for project-wide coding standards. Add
.instructions.md
files when you need different rules for different file types or frameworks. Use
AGENTS.md
if you work with multiple AI agents in your workspace.
Use a
.github/copilot-instructions.md
file
VS Code automatically detects a
.github/copilot-instructions.md
Markdown file in the root of your workspace and applies the instructions in this file to all chat requests within this workspace.
Use
copilot-instructions.md
for:
Coding style and naming conventions that apply across the project
Technology stack declarations and preferred libraries
Architectural patterns to follow or avoid
Security requirements and error handling approaches
Documentation standards
Follow these steps to create a
.github/copilot-instructions.md
file in your workspace:
Create a
.github/copilot-instructions.md
file at the root of your workspace. If needed, create a
.github
directory first.
Describe your instructions in Markdown format. Keep them concise and focused for optimal results.
Note
VS Code also supports the use of an
AGENTS.md
file
for always-on instructions.
Example: General coding guidelines
---
applyTo
:
"**"
---
# Project general coding standards
## Naming Conventions
-
Use PascalCase for component names, interfaces, and type aliases
-
Use camelCase for variables, functions, and methods
-
Prefix private class members with underscore (_)
-
Use ALL_CAPS for constants
## Error Handling
-
Use try/catch blocks for async operations
-
Implement proper error boundaries in React components
-
Always log errors with contextual information
Use
.instructions.md
files
You can create file-based instructions with
*.instructions.md
Markdown files that are applied dynamically based on the files or tasks the agent is working on.
The agent determines which instructions files to apply based on the file patterns specified in the
applyTo
property in the instructions file header or semantic matching of the instruction description to the current task.
Use
.instructions.md
files for:
Different conventions for frontend vs. backend code
Language-specific guidelines in a monorepo
Framework-specific patterns for specific modules
Specialized rules for test files or documentation
Instructions file locations
You can define instructions for a specific workspace or at the user level, where they are applied across all your workspaces. The following table lists the default file locations for instructions files based on their scope. You can configure additional file locations for workspace instructions files with the
chat.instructionsFilesLocations
Open in VS Code
Open in VS Code Insiders
setting.
Scope
Default file location
Workspace
.github/instructions
folder
Workspace (Claude format)
.claude/rules
folder
User profile
~/.copilot/instructions
,
~/.claude/rules
, or your user data (specific to your VS Code profile)
VS Code searches these folders recursively, to enable you to organize instructions files in subdirectories. For example, you can group instructions by team, language, or module:
.github/instructions/
frontend/
react.instructions.md
accessibility.instructions.md
backend/
api-design.instructions.md
testing/
unit-tests.instructions.md
The following example shows how to configure the instructions file locations to only allow workspace-level instructions:
"chat.instructionsFilesLocations"
: {
".github/instructions"
:
true
,
".claude/rules"
:
true
,
"~/.copilot/instructions"
:
false
,
"~/.claude/rules"
:
false
}
Tip
In a monorepo, enable
chat.useCustomizationsInParentRepositories
Open in VS Code
Open in VS Code Insiders
to discover instructions from the parent repository root. Learn more about
parent repository discovery
.
Instructions file format
Instructions files are Markdown files with the
.instructions.md
extension. The optional YAML frontmatter header controls when the instructions are applied:
Field
Required
Description
name
No
Display name shown in the UI. Defaults to the file name.
description
No
Short description shown on hover in the Chat view.
applyTo
No
Glob pattern that defines which files the instructions apply to automatically, relative to the workspace root. Use
**
to apply to all files. If not specified, the instructions are not applied automatically, but you can still add them manually to a chat request.
The body contains the instructions in Markdown format. To reference agent tools, use the
#tool:<tool-name>
syntax (for example,
#tool:web/fetch
).
---
name
:
'Python Standards'
description
:
'Coding conventions for Python files'
applyTo
:
'**/*.py'
---
# Python coding standards
-
Follow the PEP 8 style guide.
-
Use type hints for all function signatures.
-
Write docstrings for public functions.
-
Use 4 spaces for indentation.
Create an instructions file
When you create an instructions file, choose whether to store it in your workspace or user profile. Workspace instructions files apply only to that workspace, while user instructions files are available across multiple workspaces.
To create an instructions file:
Tip
Type
/instructions
in the chat input to quickly open the
Configure Instructions and Rules
menu.
In the Chat view, select
Configure Chat
(gear icon) to open the Agent Customizations editor and then select the
Instructions
tab.
Select
New Instructions (Workspace)
or
New Instructions (User)
from the dropdown, depending on where you want to store the instructions file.
Alternatively, use the
Chat: New Instructions File
command from the Command Palette (
⇧⌘P
(Windows, Linux
Ctrl+Shift+P
)
).
Select the location and enter a file name for your instructions file. This is the default name that is used in the UI.
Author the custom instructions by using Markdown formatting.
Fill in the YAML frontmatter at the top of the file to configure the instructions' description, name, and when they apply.
Add instructions in the body of the file.
You can modify existing instruction files by opening them in the Agent Customizations editor.
Generate an instructions file with AI
You can use AI to generate a targeted instructions file. Type
/create-instruction
in chat and describe the convention or guideline you want to enforce (for example, "always use tabs and single quotes in this project"). The agent asks clarifying questions and generates an
.instructions.md
file with the appropriate
applyTo
pattern and content.
You can also extract instructions from an ongoing conversation. For example, if you corrected the agent's import style during a chat session, ask "extract an instruction from this" to capture that correction as a project convention.
Note
/create-instruction
generates targeted, on-demand instruction files. To generate workspace-wide always-on instructions, use the
/init
command
instead.
Example: Language-specific coding guidelines
Notice how these instructions reference the general coding guidelines file. You can separate the instructions into multiple files to keep them organized and focused on specific topics.
---
applyTo
:
"**/*.ts,**/*.tsx"
---
# Project coding standards for TypeScript and React
Apply the [
general coding guidelines
](
./general-coding.instructions.md
) to all code.
## TypeScript Guidelines
-
Use TypeScript for all new code
-
Follow functional programming principles where possible
-
Use interfaces for data structures and type definitions
-
Prefer immutable data (const, readonly)
-
Use optional chaining (?.) and nullish coalescing (??) operators
## React Guidelines
-
Use functional components with hooks
-
Follow the React hooks rules (no conditional hooks)
-
Use React.FC type for components with children
-
Keep components small and focused
-
Use CSS modules for component styling
Example: Documentation writing guidelines
You can create instructions files for different types of tasks, including non-development activities like writing documentation.
---
applyTo
:
"docs/**/*.md"
---
# Project documentation writing guidelines
## General Guidelines
-
Write clear and concise documentation.
-
Use consistent terminology and style.
-
Include code examples where applicable.
## Grammar
*
Use present tense verbs (is, open) instead of past tense (was, opened).
*
Write factual statements and direct commands. Avoid hypotheticals like "could" or "would".
*
Use active voice where the subject performs the action.
*
Write in second person (you) to speak directly to readers.
## Markdown Guidelines
-
Use headings to organize content.
-
Use bullet points for lists.
-
Include links to related resources.
-
Use code blocks for code snippets.
For more community-contributed examples, see the
Awesome Copilot repository
.
Use an
AGENTS.md
file
VS Code automatically detects an
AGENTS.md
Markdown file in the root of your workspace and applies the instructions in this file to all chat requests within this workspace. This is useful if you work with multiple AI agents in your workspace and want a single set of instructions recognized by all of them, or if you want subfolder-level instructions that apply to specific parts of a monorepo.
Us
