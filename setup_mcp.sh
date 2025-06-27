
# TODO replace token with actual value, but not in the code. We should take it as argument
claude mcp add-json github '{ "mcpServers": { "github": { "command": "docker", "args": [ "run", "-i", "--rm", "-e", "GITHUB_PERSONAL_ACCESS_TOKEN", "ghcr.io/github/github-mcp-server" ], "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "$TOKEN" } } } }'