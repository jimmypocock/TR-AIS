/**
 * /help command - Show available commands
 */

module.exports = {
    name: "help",
    aliases: ["?"],
    description: "Show available commands",

    execute(args, context) {
        const { commands } = context;

        // Build help text from registered commands
        const commandList = Object.values(commands)
            .map(cmd => {
                const aliases = cmd.aliases.length > 0
                    ? ` (or /${cmd.aliases.join(", /")})`
                    : "";
                return `• **/${cmd.name}**${aliases} - ${cmd.description}`;
            })
            .join("\n");

        return {
            thinking: "User requested help",
            commands: [],
            response: `**Available Commands:**\n${commandList}\n\nOr just chat naturally about your track!`
        };
    }
};
