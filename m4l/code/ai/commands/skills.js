/**
 * /skills command - List available skills
 */

const { discoverSkills } = require("../config");

module.exports = {
    name: "skills",
    aliases: ["listskills"],
    description: "List available skills",

    execute(args, context) {
        const skills = discoverSkills();

        if (skills.length === 0) {
            return {
                thinking: "No skills found",
                commands: [],
                response: "No skills found.\n\nAdd skills by creating folders in:\n~/Library/Application Support/ChatM4L/skills/\n\nEach skill needs a SKILL.md file."
            };
        }

        const { currentSkill } = context;
        const activeIndicator = (name) => currentSkill?.name === name ? " (active)" : "";

        const skillList = skills
            .map(s => `• **/${s.name}**${activeIndicator(s.name)} - ${s.title}`)
            .join("\n");

        return {
            thinking: "Listing available skills",
            commands: [],
            response: `**Available Skills:**\n${skillList}\n\nUse /<skill-name> to activate.\nUse /skill off to deactivate.`
        };
    }
};
