/**
 * Command Router - Handles slash commands
 *
 * Commands are loaded from individual files in this directory.
 * Each command exports: { name, aliases, description, execute(args, context) }
 *
 * Also supports dynamic skill activation via /<skillname>
 */

const { loadSkill } = require("../config");

// Load all commands
const newchat = require("./newchat");
const status = require("./status");
const help = require("./help");
const createconfig = require("./createconfig");
const reload = require("./reload");
const openconfig = require("./openconfig");
const skills = require("./skills");
const skill = require("./skill");

// Register commands by name and aliases
const commands = {};
const commandModules = [
    newchat,
    status,
    help,
    createconfig,
    reload,
    openconfig,
    skills,
    skill
];

for (const cmd of commandModules) {
    commands[cmd.name] = cmd;
    for (const alias of cmd.aliases) {
        commands[alias] = cmd;
    }
}

/**
 * Check if a command name matches a skill and activate it
 * @param {string} commandName - The skill name to activate
 * @param {string} remainingText - Any text after the skill name (the actual request)
 * @param {object} context - Command context
 * @returns {object|null} - Response object, or { passthrough: message } to continue to AI
 */
function tryActivateSkill(commandName, remainingText, context) {
    const loadedSkill = loadSkill(commandName);

    if (loadedSkill) {
        context.setCurrentSkill(loadedSkill);

        // If there's remaining text, activate skill and pass the text to AI
        if (remainingText && remainingText.trim()) {
            return {
                passthrough: remainingText.trim(),
                skillActivated: loadedSkill.title
            };
        }

        // No additional text - just show activation message
        return {
            thinking: `Activated ${loadedSkill.name} skill`,
            commands: [],
            response: `**${loadedSkill.title}** activated!\n\nI'll now apply this expertise to our conversation.`
        };
    }

    return null;
}

/**
 * Parse and execute a slash command
 *
 * @param {string} message - The user's message (e.g., "/newchat" or "/drums")
 * @param {object} context - Context object with trackName, currentSession, maxAPI, etc.
 * @returns {object|null} - Response object if command handled, null if not a command
 */
function handleCommand(message, context) {
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

    if (command) {
        // Add commands registry to context for /help
        const enrichedContext = {
            ...context,
            commands: commandModules.reduce((acc, cmd) => {
                acc[cmd.name] = cmd;
                return acc;
            }, {})
        };

        return command.execute(args, enrichedContext);
    }

    // Try to activate a skill with this name
    const skillResult = tryActivateSkill(commandName, args, context);
    if (skillResult) {
        return skillResult;
    }

    // Unknown command
    return {
        thinking: "Unknown command",
        commands: [],
        response: `Unknown command: /${commandName}\n\nType /help for commands.\nType /skills for available skills.`
    };
}

/**
 * Get list of all registered commands
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
