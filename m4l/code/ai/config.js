/**
 * ChatM4L Config - Configuration and content management
 *
 * Handles:
 * - config.json (providers, settings)
 * - prompts/system.md (main system prompt)
 * - skills/ (auto-discovered skill prompts)
 */

const fs = require("fs");
const path = require("path");
const os = require("os");

// User config location: ~/Library/Application Support/ChatM4L/
const CONFIG_DIR = path.join(os.homedir(), "Library", "Application Support", "ChatM4L");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");
const PROMPTS_DIR = path.join(CONFIG_DIR, "prompts");
const SKILLS_DIR = path.join(CONFIG_DIR, "skills");
const SESSIONS_DIR = path.join(CONFIG_DIR, "sessions");

// Defaults bundled with the device
const DEFAULTS_DIR = path.join(__dirname, "defaults");

// =============================================================================
// DIRECTORY MANAGEMENT
// =============================================================================

/**
 * Ensure all required directories exist
 */
function ensureDirectories() {
    const dirs = [CONFIG_DIR, PROMPTS_DIR, SKILLS_DIR, SESSIONS_DIR];
    for (const dir of dirs) {
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }
    }
}

// =============================================================================
// CONFIG FILE MANAGEMENT
// =============================================================================

/**
 * Load config.json
 */
function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_FILE)) {
            const data = fs.readFileSync(CONFIG_FILE, "utf8");
            return JSON.parse(data);
        }
    } catch (e) {
        console.error("Error loading config:", e.message);
    }
    return null;
}

/**
 * Save config.json
 */
function saveConfig(config) {
    try {
        ensureDirectories();
        fs.writeFileSync(CONFIG_FILE, JSON.stringify(config, null, 2));
        return true;
    } catch (e) {
        console.error("Error saving config:", e.message);
        return false;
    }
}

/**
 * Check if config exists and is valid
 */
function isConfigValid() {
    const config = loadConfig();
    if (!config) return false;
    if (!config.providers) return false;
    if (!config.activeProvider) return false;
    return true;
}

/**
 * Get the active provider config
 */
function getActiveProvider(config) {
    if (!config || !config.providers || !config.activeProvider) {
        return null;
    }
    return config.providers[config.activeProvider] || null;
}

/**
 * Get the active model name
 */
function getActiveModel(config) {
    const provider = getActiveProvider(config);
    if (!provider || !provider.models) return null;

    const modelKey = config.activeModel || "default";
    return provider.models[modelKey] || provider.models.default || null;
}

// =============================================================================
// DEFAULT CONFIG CREATION
// =============================================================================

/**
 * Back up existing config file
 */
function backupConfig() {
    if (!fs.existsSync(CONFIG_FILE)) return null;

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
    const backupPath = CONFIG_FILE.replace(".json", `.${timestamp}.bak`);

    try {
        fs.copyFileSync(CONFIG_FILE, backupPath);
        return backupPath;
    } catch (e) {
        console.error("Error backing up config:", e.message);
        return null;
    }
}

/**
 * Copy a directory recursively
 */
function copyDirSync(src, dest) {
    if (!fs.existsSync(src)) return;

    fs.mkdirSync(dest, { recursive: true });

    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const entry of entries) {
        const srcPath = path.join(src, entry.name);
        const destPath = path.join(dest, entry.name);

        if (entry.isDirectory()) {
            copyDirSync(srcPath, destPath);
        } else {
            fs.copyFileSync(srcPath, destPath);
        }
    }
}

/**
 * Create default config from bundled defaults
 * Backs up existing config if present
 */
function createDefaultConfig() {
    ensureDirectories();

    // Back up existing config
    const backupPath = backupConfig();

    // Copy default config.json
    const defaultConfig = path.join(DEFAULTS_DIR, "config.json");
    if (fs.existsSync(defaultConfig)) {
        fs.copyFileSync(defaultConfig, CONFIG_FILE);
    }

    // Copy default prompts
    const defaultPrompts = path.join(DEFAULTS_DIR, "prompts");
    if (fs.existsSync(defaultPrompts)) {
        copyDirSync(defaultPrompts, PROMPTS_DIR);
    }

    // Copy default skills
    const defaultSkills = path.join(DEFAULTS_DIR, "skills");
    if (fs.existsSync(defaultSkills)) {
        copyDirSync(defaultSkills, SKILLS_DIR);
    }

    return {
        created: true,
        backupPath,
        configPath: CONFIG_FILE
    };
}

// =============================================================================
// PROMPT LOADING
// =============================================================================

/**
 * Load the main system prompt from prompts/system.md
 */
function loadSystemPrompt() {
    const promptPath = path.join(PROMPTS_DIR, "system.md");

    try {
        if (fs.existsSync(promptPath)) {
            return fs.readFileSync(promptPath, "utf8");
        }
    } catch (e) {
        console.error("Error loading system prompt:", e.message);
    }

    // Fallback to bundled default
    const defaultPath = path.join(DEFAULTS_DIR, "prompts", "system.md");
    try {
        if (fs.existsSync(defaultPath)) {
            return fs.readFileSync(defaultPath, "utf8");
        }
    } catch (e) {
        console.error("Error loading default system prompt:", e.message);
    }

    return "You are ChatM4L, an AI assistant for Ableton Live.";
}

// =============================================================================
// SKILLS MANAGEMENT
// =============================================================================

/**
 * Discover all skills in the skills directory
 * Returns array of { name, path, prompt }
 */
function discoverSkills() {
    const skills = [];

    try {
        if (!fs.existsSync(SKILLS_DIR)) return skills;

        const entries = fs.readdirSync(SKILLS_DIR, { withFileTypes: true });

        for (const entry of entries) {
            if (!entry.isDirectory()) continue;

            const skillPath = path.join(SKILLS_DIR, entry.name);
            const skillFile = path.join(skillPath, "SKILL.md");

            if (fs.existsSync(skillFile)) {
                const prompt = fs.readFileSync(skillFile, "utf8");

                // Extract title from first heading
                const titleMatch = prompt.match(/^#\s+(.+)/m);
                const title = titleMatch ? titleMatch[1] : entry.name;

                skills.push({
                    name: entry.name,
                    title,
                    path: skillPath,
                    prompt
                });
            }
        }
    } catch (e) {
        console.error("Error discovering skills:", e.message);
    }

    return skills;
}

/**
 * Load a specific skill by name
 */
function loadSkill(skillName) {
    const skillPath = path.join(SKILLS_DIR, skillName, "SKILL.md");

    try {
        if (fs.existsSync(skillPath)) {
            const prompt = fs.readFileSync(skillPath, "utf8");
            const titleMatch = prompt.match(/^#\s+(.+)/m);

            return {
                name: skillName,
                title: titleMatch ? titleMatch[1] : skillName,
                prompt
            };
        }
    } catch (e) {
        console.error(`Error loading skill '${skillName}':`, e.message);
    }

    return null;
}

// =============================================================================
// EXPORTS
// =============================================================================

module.exports = {
    // Paths
    CONFIG_DIR,
    CONFIG_FILE,
    PROMPTS_DIR,
    SKILLS_DIR,
    SESSIONS_DIR,
    DEFAULTS_DIR,

    // Config management
    loadConfig,
    saveConfig,
    isConfigValid,
    getActiveProvider,
    getActiveModel,
    backupConfig,
    createDefaultConfig,
    ensureDirectories,

    // Prompts
    loadSystemPrompt,

    // Skills
    discoverSkills,
    loadSkill
};
