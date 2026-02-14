/**
 * /newchat command - Start a fresh conversation
 *
 * Archives the current session and starts a new one.
 */

const { clearSession } = require("../sessions");

module.exports = {
    name: "newchat",
    aliases: ["new"],
    description: "Start a fresh conversation (archives current chat)",

    execute(args, context) {
        const { trackName, maxAPI, setCurrentSession } = context;

        const newSession = clearSession(trackName);
        setCurrentSession(newSession);

        maxAPI.post("New session started: " + newSession.id);

        return {
            thinking: "User requested a new chat session",
            commands: [],
            response: "Started a fresh conversation. Previous chat has been archived. How can I help you?"
        };
    }
};
