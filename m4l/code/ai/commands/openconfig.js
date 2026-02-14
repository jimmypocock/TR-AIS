/**
 * /openconfig command - Show config directory path
 */

const { CONFIG_DIR } = require("../config");

module.exports = {
    name: "openconfig",
    aliases: ["config", "configpath"],
    description: "Show config directory location",

    execute(args, context) {
        return {
            thinking: "User wants to know where config is located",
            commands: [],
            response: `**Config Location:**\n${CONFIG_DIR}\n\n**Files:**\n• config.json - API keys and settings\n• prompts/system.md - System prompt\n• skills/ - Skill prompts`
        };
    }
};
