/**
 * /createconfig command - Create default config from bundled defaults
 */

const { createDefaultConfig } = require("../config");

module.exports = {
    name: "createconfig",
    aliases: ["initconfig", "resetconfig", "configreset"],
    description: "Create or reset config from defaults (backs up existing)",

    execute(args, context) {
        const { maxAPI } = context;

        const result = createDefaultConfig();

        if (result.created) {
            maxAPI.post("Config created at: " + result.configPath);
            if (result.backupPath) {
                maxAPI.post("Previous config backed up to: " + result.backupPath);
            }

            let response = `Config created!\n\nEdit your API key in:\n${result.configPath}\n\nThen run /reload to apply changes.`;

            if (result.backupPath) {
                response += `\n\nPrevious config backed up.`;
            }

            return {
                thinking: "Created default configuration",
                commands: [],
                response
            };
        }

        return {
            thinking: "Failed to create config",
            commands: [],
            response: "Failed to create config. Check the Max console for details."
        };
    }
};
