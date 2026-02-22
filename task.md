Build an personal AI agent MVP

Features
- User can ask question using chat
- System will call LLM and take actions
- System will have tools to use
- tools
    - file system: read, write, search
    - exec command
 
- Maintain memory as markdown files, create workspace folder
    - USER.md : user information eg. name, age, location timezone etc
    - AGENT_IDENTITY.md : Name, tone, style 
    - MEMORY.md : user preferences eg. like cursor, python etc (its long term memory)
    - AGENT.md : Rules, how agent should act. eg. what are memory fiels to read, when to update memory etc
- Matain session as jsonl file, create session folder
- Manage context as follows
    - pass all above memory files in system instruction
    - pass all previous chats from session for context
- if LLM return to execute tool, do this and call ll with response following agentic loop



Tech contrains
- No UI, user will interact using command line
- Use python
- Use open ai sdk
- Use gemini2.0-flash model
- Use venv
- use uv command to create venv and add libraries
- use minimal code
- log all LLM and tool calls for debugging
- add api key in .env


Future scope
- Can be installed into any system
- Can be used with any model and provider
- More tools can be added
- User can talk to agent using audio
- Agent will have crons for schedules task


Todo:
- Delete agent.log
- 