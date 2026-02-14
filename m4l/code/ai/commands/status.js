/**
 * /status command - Show current session info
 */

const { getMessageCount } = require("../sessions");

module.exports = {
    name: "status",
    aliases: [],
    description: "Show current session info",

    execute(args, context) {
        const { trackName, currentSession } = context;

        const status = {
            track: trackName,
            sessionId: currentSession ? currentSession.id : "none",
            messageCount: currentSession ? getMessageCount(currentSession) : 0,
            provider: "anthropic",
            model: "claude-sonnet-4-20250514"
        };

        return {
            thinking: "User requested status info",
            commands: [],
            response: [
                `**Track:** ${status.track}`,
                `**Session:** ${status.sessionId}`,
                `**Messages:** ${status.messageCount}`,
                `**Model:** ${status.model}`
            ].join("\n")
        };
    }
};
