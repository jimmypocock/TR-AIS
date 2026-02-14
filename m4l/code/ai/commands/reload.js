/**
 * /reload command - Reload config and reinitialize client
 */

module.exports = {
    name: "reload",
    aliases: ["reloadconfig"],
    description: "Reload config after editing (auto-loads on Ableton restart)",

    execute(args, context) {
        // Note: This command is handled directly in main.js
        // because it needs access to initializeFromConfig()
        // This file exists for /help to discover it

        return {
            thinking: "Reload command - delegating to main handler",
            commands: [],
            response: "Reloading config..."
        };
    }
};
