/**
 * ChatM4L Config - Configuration file management
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

// Config file location: ~/Library/Application Support/ChatM4L/config.json
const CONFIG_DIR = path.join(os.homedir(), "Library", "Application Support", "ChatM4L");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");

function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_FILE)) {
            const data = fs.readFileSync(CONFIG_FILE, "utf8");
            return JSON.parse(data);
        }
    } catch (e) {
        console.error("Error loading config:", e.message);
    }
    return {};
}

function saveConfig(config) {
    try {
        // Create directory if it doesn't exist
        if (!fs.existsSync(CONFIG_DIR)) {
            fs.mkdirSync(CONFIG_DIR, { recursive: true });
        }
        fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
        return true;
    } catch (e) {
        console.error("Error saving config:", e.message);
        return false;
    }
}

module.exports = {
    CONFIG_DIR,
    CONFIG_FILE,
    loadConfig,
    saveConfig
};
