/**
 * /help command - Show available commands
 */

const { discoverSkills } = require("../config");

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

        // Get available skills
        const skills = discoverSkills();
        const skillTip = skills.length > 0
            ? `\n\n**Skills:** ${skills.map(s => `/${s.name}`).join(", ")}\nActivate with /<skill-name> or /skills to see all.`
            : "";

        return {
            thinking: "User requested help",
            commands: [],
            response: `**Commands:**\n${commandList}${skillTip}\n\nOr just chat naturally about your track!`
        };
    }
};
