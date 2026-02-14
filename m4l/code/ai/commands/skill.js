/**
 * /skill command - Activate or deactivate a skill
 *
 * Usage:
 *   /skill drums     - Activate the drums skill
 *   /skill off       - Deactivate current skill
 *   /skill           - Show current skill
 */

const { loadSkill, discoverSkills } = require("../config");

module.exports = {
    name: "skill",
    aliases: [],
    description: "Activate, deactivate, or show current skill",

    execute(args, context) {
        const { currentSkill, setCurrentSkill } = context;

        // No args - show current skill
        if (!args || args.trim() === "") {
            if (currentSkill) {
                return {
                    thinking: "Showing current skill",
                    commands: [],
                    response: `**Active Skill:** ${currentSkill.title}\n\nUse /skill off to deactivate.`
                };
            } else {
                return {
                    thinking: "No active skill",
                    commands: [],
                    response: "No skill active.\n\nUse /skills to see available skills."
                };
            }
        }

        const skillName = args.trim().toLowerCase();

        // Deactivate skill
        if (skillName === "off" || skillName === "none" || skillName === "reset") {
            if (currentSkill) {
                const wasActive = currentSkill.title;
                setCurrentSkill(null);
                return {
                    thinking: "Deactivating skill",
                    commands: [],
                    response: `Deactivated **${wasActive}** skill.\n\nBack to default mode.`
                };
            } else {
                return {
                    thinking: "No skill to deactivate",
                    commands: [],
                    response: "No skill is currently active."
                };
            }
        }

        // Try to load the skill
        const skill = loadSkill(skillName);

        if (!skill) {
            const available = discoverSkills();
            const suggestions = available.map(s => s.name).join(", ");

            return {
                thinking: "Skill not found",
                commands: [],
                response: `Skill '${skillName}' not found.\n\nAvailable: ${suggestions || "none"}`
            };
        }

        // Activate skill
        setCurrentSkill(skill);

        return {
            thinking: `Activated ${skill.name} skill`,
            commands: [],
            response: `**${skill.title}** activated!\n\nI'll now apply this expertise to our conversation.`
        };
    }
};
