/**
 * Command Router - Handles slash commands like /newchat, /status, etc.
 *
 * Commands are loaded from individual files in this directory.
 * Each command exports: { name, aliases, description, execute(args, context) }
 */

// Load all commands
const newchat = require("./newchat");
const status = require("./status");
const help = require("./help");

// Register commands by name and aliases
const commands = {};
const commandModules = [newchat, status, help];

for (const cmd of commandModules) {
    commands[cmd.name] = cmd;
    for (const alias of cmd.aliases) {
        commands[alias] = cmd;
    }
}

/**
 * Parse and execute a slash command
 *
 * @param {string} message - The user's message (e.g., "/newchat" or "/status")
 * @param {object} context - Context object with trackName, currentSession, maxAPI, etc.
 * @returns {object|null} - Response object if command handled, null if not a command
 */
function handleCommand(message, context) {
    // Check if it's a command
    if (!message.startsWith("/")) {
        return null;
    }

    // Parse command and args
    const trimmed = message.slice(1).trim();
    const spaceIndex = trimmed.indexOf(" ");
    const commandName = (spaceIndex === -1 ? trimmed : trimmed.slice(0, spaceIndex)).toLowerCase();
    const args = spaceIndex === -1 ? "" : trimmed.slice(spaceIndex + 1).trim();

    // Find command
    const command = commands[commandName];

    if (!command) {
        return {
            thinking: "Unknown command",
            commands: [],
            response: `Unknown command: /${commandName}\n\nType /help for available commands.`
        };
    }

    // Execute command with context (include commands registry for /help)
    return command.execute(args, { ...context, commands: commandModules.reduce((acc, cmd) => {
        acc[cmd.name] = cmd;
        return acc;
    }, {}) });
}

/**
 * Get list of all registered commands (for external use)
 */
function getCommands() {
    return commandModules.map(cmd => ({
        name: cmd.name,
        aliases: cmd.aliases,
        description: cmd.description
    }));
}

module.exports = {
    handleCommand,
    getCommands
};
