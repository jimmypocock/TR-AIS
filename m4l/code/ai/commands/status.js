/**
 * /status command - Show current session and config info
 */

const { getMessageCount } = require("../sessions");
const { discoverSkills } = require("../config");
const { getProvider, getModel, isReady } = require("../client");

module.exports = {
    name: "status",
    aliases: [],
    description: "Show current session and config info",

    execute(args, context) {
        const { trackName, currentSession, currentSkill } = context;
        const skills = discoverSkills();

        const lines = [
            `**Status**`,
            ``,
            `**AI:** ${isReady() ? `${getProvider()} / ${getModel()}` : "Not configured"}`,
            `**Track:** ${trackName || "none"}`,
            `**Session:** ${currentSession ? currentSession.id : "none"}`,
            `**Messages:** ${currentSession ? getMessageCount(currentSession) : 0}`,
            `**Active Skill:** ${currentSkill ? currentSkill.title : "none"}`,
            `**Available Skills:** ${skills.length > 0 ? skills.map(s => s.name).join(", ") : "none"}`
        ];

        return {
            thinking: "Showing status info",
            commands: [],
            response: lines.join("\n")
        };
    }
};
