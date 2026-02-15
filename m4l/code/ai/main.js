/**
 * ChatM4L AI - node.script entry point for Max for Live
 *
 * This script runs in the node.script object and handles:
 * - Multi-provider AI calls (Anthropic, OpenAI, Ollama, etc.)
 * - Message processing with conversation history
 * - Slash commands and skills
 *
 * Communication with Max:
 *   Input: Messages from bridge.js (v8 object)
 *   Output: Responses via maxAPI.outlet()
 */

const maxAPI = require("max-api");

// Import modules
const {
    loadConfig,
    saveConfig,
    isConfigValid,
    getActiveProvider,
    getActiveModel,
    createDefaultConfig,
    loadSystemPrompt,
    loadUserProfile,
    discoverSkills,
    loadSkill,
    CONFIG_FILE,
    CONFIG_DIR,
    SESSIONS_DIR
} = require("./config");

const {
    initializeClient,
    sendMessage,
    getProvider,
    getModel,
    clearClient,
    isReady
} = require("./client");

const {
    getOrCreateSession,
    addMessage,
    getMessages,
    clearSession,
    getMessageCount
} = require("./sessions");

const { handleCommand } = require("./commands");

// =============================================================================
// STATE
// =============================================================================

let currentTrackName = null;
let currentSession = null;
let currentSkill = null;
let systemPrompt = null;
let userProfile = null;
let appConfig = null;

// =============================================================================
// INITIALIZATION
// =============================================================================

maxAPI.post("ChatM4L AI module loading...");

/**
 * Initialize the AI client from config
 */
function initializeFromConfig() {
    appConfig = loadConfig();

    if (!appConfig) {
        maxAPI.post("No config found. Use /createconfig to create one.");
        maxAPI.outlet("needsconfig");
        return false;
    }

    if (!isConfigValid()) {
        maxAPI.post("Invalid config. Use /createconfig to reset.");
        maxAPI.outlet("needsconfig");
        return false;
    }

    const providerName = appConfig.activeProvider;
    const providerConfig = getActiveProvider(appConfig);
    const modelKey = appConfig.activeModel || "default";

    if (!providerConfig) {
        maxAPI.post(`Provider '${providerName}' not found in config`);
        maxAPI.outlet("needsconfig");
        return false;
    }

    // Check for API key (not needed for local models like Ollama)
    if (!providerConfig.baseUrl && (!providerConfig.apiKey || providerConfig.apiKey.startsWith("YOUR_"))) {
        maxAPI.post(`API key not configured for ${providerName}. Edit config.json.`);
        maxAPI.outlet("needsconfig");
        return false;
    }

    if (initializeClient(providerName, providerConfig, modelKey)) {
        maxAPI.post(`Initialized: ${providerName} / ${getModel()}`);

        // Load system prompt
        systemPrompt = loadSystemPrompt();
        maxAPI.post("System prompt loaded");

        // Load user profile (optional)
        userProfile = loadUserProfile();
        if (userProfile) {
            maxAPI.post("User profile loaded");
        } else {
            maxAPI.post("No user profile (edit core/user.md to personalize)");
        }

        // Discover available skills
        const skills = discoverSkills();
        maxAPI.post(`Found ${skills.length} skills: ${skills.map(s => s.name).join(", ") || "none"}`);

        maxAPI.outlet("ready");
        sendStatus();
        return true;
    }

    maxAPI.outlet("error", "Failed to initialize AI client");
    return false;
}

// Run initialization
initializeFromConfig();

// =============================================================================
// CHAT HANDLING
// =============================================================================

maxAPI.addHandler("chat", async (payloadJson) => {
    maxAPI.post("Chat handler called");

    try {
        const payload = JSON.parse(payloadJson);
        let { message } = payload;
        const { context } = payload;

        // Handle bootstrap commands first (these work without config)
        if (message.startsWith("/")) {
            const cmd = message.slice(1).split(" ")[0].toLowerCase();

            if (cmd === "createconfig" || cmd === "resetconfig" || cmd === "initconfig" || cmd === "configreset") {
                maxAPI.post("Bootstrap command: createconfig");
                const result = createDefaultConfig();
                if (result.created) {
                    maxAPI.post("Config created at: " + result.configPath);
                    if (result.backupPath) {
                        maxAPI.post("Previous config backed up to: " + result.backupPath);
                    }
                    maxAPI.outlet("response", JSON.stringify({
                        thinking: "Created default configuration",
                        commands: [],
                        response: `Config created!\n\nEdit your API key in:\n${result.configPath}\n\nThen run /reload to apply changes.`
                    }));
                } else {
                    maxAPI.outlet("error", "Failed to create config");
                }
                return;
            }

            if (cmd === "reload" || cmd === "reloadconfig") {
                maxAPI.post("Bootstrap command: reload");
                clearClient();
                currentSkill = null;
                if (initializeFromConfig()) {
                    maxAPI.outlet("response", JSON.stringify({
                        thinking: "Reloaded configuration",
                        commands: [],
                        response: `Reloaded!\n\nProvider: ${getProvider()}\nModel: ${getModel()}`
                    }));
                }
                return;
            }

            if (cmd === "openconfig") {
                maxAPI.post("Bootstrap command: openconfig");
                maxAPI.outlet("response", JSON.stringify({
                    thinking: "User wants to open config directory",
                    commands: [],
                    response: `Config location:\n${CONFIG_DIR}\n\nFiles:\n• config.json - API keys and settings\n• prompts/system.md - System prompt\n• skills/ - Skill prompts`
                }));
                return;
            }
        }

        // For everything else, check if client is ready
        if (!isReady()) {
            maxAPI.post("No client initialized");
            maxAPI.outlet("error", "Not configured. Run /createconfig then edit config.json");
            return;
        }

        // Get track name from context
        const trackName = context.trackName || context.name || "unknown";

        // Track changes
        if (currentTrackName && currentTrackName !== trackName) {
            maxAPI.post("Track changed: " + currentTrackName + " -> " + trackName);
        }
        currentTrackName = trackName;

        // Handle other slash commands (these need client to be ready)
        if (message.startsWith("/")) {
            maxAPI.post("Command detected: " + message);

            const commandContext = {
                trackName,
                currentSession,
                currentSkill,
                maxAPI,
                setCurrentSession: (session) => { currentSession = session; },
                setCurrentSkill: (skill) => {
                    currentSkill = skill;
                    sendStatus();  // Update UI when skill changes
                }
            };

            const result = handleCommand(message, commandContext);
            if (result) {
                // Check if this is a skill activation with passthrough text
                if (result.passthrough) {
                    // Skill was activated for this message only (one-shot)
                    maxAPI.post("Skill activated (one-shot): " + result.skillActivated + ", processing: " + result.passthrough);
                    message = result.passthrough;
                    // Continue to AI processing below (skill will be cleared after response)
                } else {
                    // Regular command response - return immediately
                    maxAPI.outlet("response", JSON.stringify(result));
                    return;
                }
            }
        }

        // Skills activated via passthrough are one-shot (cleared after this message)
        // Skills activated via /skill command persist until manually deactivated
        const isOneShotSkill = message !== payload.message && currentSkill;

        maxAPI.post("Processing on track '" + trackName + "': " + message);

        // Get or create session
        currentSession = getOrCreateSession(trackName);

        // Store user message
        addMessage(currentSession, "user", message);

        // Build messages with context injected into latest
        const history = getMessages(currentSession);
        const messagesForAI = history.map((msg, i) => {
            if (i === history.length - 1 && msg.role === "user") {
                return {
                    role: "user",
                    content: `Current track state:\n${JSON.stringify(context, null, 2)}\n\nUser request: ${msg.content}`
                };
            }
            return msg;
        });

        // Build full prompt (system + user profile + skill if active)
        let fullPrompt = systemPrompt;
        if (userProfile) {
            fullPrompt += "\n\n---\n\n" + userProfile;
        }
        if (currentSkill) {
            fullPrompt += "\n\n---\n\n" + currentSkill.prompt;
        }

        maxAPI.post(`Sending ${messagesForAI.length} messages to ${getProvider()}/${getModel()}`);

        // Send to AI
        const responseText = await sendMessage(fullPrompt, messagesForAI, {
            maxTokens: appConfig?.settings?.maxTokens || 1024
        });

        maxAPI.post("Raw response: " + responseText.substring(0, 100) + "...");

        // Store assistant response
        addMessage(currentSession, "assistant", responseText);

        // Parse JSON response
        let result;
        try {
            result = JSON.parse(responseText);
        } catch (directParseError) {
            try {
                const jsonMatch = responseText.match(/\{[\s\S]*\}/);
                if (jsonMatch) {
                    result = JSON.parse(jsonMatch[0]);
                } else {
                    throw new Error("No JSON found in response");
                }
            } catch (extractError) {
                maxAPI.post("Parse error: " + extractError.message);

                // Check if it looks like a truncated response
                const isTruncated = responseText.length > 500 &&
                    (responseText.endsWith("...") ||
                     !responseText.trim().endsWith("}") ||
                     extractError.message.includes("position"));

                let errorMessage;
                if (isTruncated) {
                    errorMessage = "Response was too long and got cut off. Try a simpler request, or increase maxTokens in your config.json and run /reload.";
                } else {
                    errorMessage = "Had trouble understanding the AI response. Try rephrasing your request.";
                }

                result = {
                    thinking: "Response parsing failed",
                    commands: [],
                    response: errorMessage
                };
            }
        }

        maxAPI.outlet("response", JSON.stringify(result));

        // Clear skill after one-shot use (e.g., "/drums make a beat")
        // Skills activated via /skill command persist until manually deactivated
        if (isOneShotSkill) {
            currentSkill = null;
            sendStatus();
            maxAPI.post("Skill cleared after one-shot use");
        }

    } catch (e) {
        maxAPI.post("Error: " + e.message);

        let userMessage;
        const errorLower = e.message.toLowerCase();

        if (errorLower.includes("401") || errorLower.includes("invalid") || errorLower.includes("authentication")) {
            userMessage = "Invalid API key - check your config.json";
        } else if (errorLower.includes("429") || errorLower.includes("rate")) {
            userMessage = "Rate limited - wait a moment and try again";
        } else if (errorLower.includes("network") || errorLower.includes("fetch") || errorLower.includes("connect")) {
            userMessage = "Network error - check your connection";
        } else if (errorLower.includes("timeout")) {
            userMessage = "Request timed out - try again";
        } else {
            userMessage = "Something went wrong - try again";
        }

        maxAPI.outlet("error", userMessage);
    }
});

// =============================================================================
// CONFIG HANDLERS
// =============================================================================

// Create default config (copies from bundled defaults)
maxAPI.addHandler("createconfig", () => {
    const result = createDefaultConfig();

    if (result.created) {
        maxAPI.post("Config created at: " + result.configPath);
        if (result.backupPath) {
            maxAPI.post("Previous config backed up to: " + result.backupPath);
        }
        maxAPI.outlet("response", JSON.stringify({
            thinking: "Created default configuration",
            commands: [],
            response: `Config created!\n\nEdit your API key in:\n${result.configPath}\n\nThen run /reload to apply changes.`
        }));
    } else {
        maxAPI.outlet("error", "Failed to create config");
    }
});

// Reload config
maxAPI.addHandler("reload", () => {
    clearClient();
    currentSkill = null;

    if (initializeFromConfig()) {
        maxAPI.outlet("response", JSON.stringify({
            thinking: "Reloaded configuration",
            commands: [],
            response: `Reloaded!\n\nProvider: ${getProvider()}\nModel: ${getModel()}`
        }));
    }
});

// Open config directory (outputs path for user to navigate to)
maxAPI.addHandler("openconfig", () => {
    maxAPI.outlet("response", JSON.stringify({
        thinking: "User wants to open config directory",
        commands: [],
        response: `Config location:\n${CONFIG_DIR}\n\nFiles:\n• config.json - API keys and settings\n• prompts/system.md - System prompt\n• skills/ - Skill prompts`
    }));
});

// =============================================================================
// STATUS BROADCAST
// =============================================================================

/**
 * Send current status to bridge.js for UI updates
 */
function sendStatus() {
    const skills = discoverSkills();
    const status = {
        ready: isReady(),
        provider: getProvider(),
        model: getModel(),
        configPath: CONFIG_FILE,
        currentTrack: currentTrackName,
        sessionId: currentSession ? currentSession.id : null,
        messageCount: currentSession ? getMessageCount(currentSession) : 0,
        activeSkill: currentSkill ? currentSkill.name : null,
        availableSkills: skills.map(s => s.name)
    };
    maxAPI.outlet("status", JSON.stringify(status));
}

// =============================================================================
// UTILITY HANDLERS
// =============================================================================

maxAPI.addHandler("ping", () => {
    maxAPI.outlet("pong");
    maxAPI.post("Pong!");
});

maxAPI.addHandler("status", () => {
    sendStatus();
    maxAPI.post("Status sent to bridge");
});

// Clear session
maxAPI.addHandler("clearchat", () => {
    if (currentTrackName) {
        currentSession = clearSession(currentTrackName);
        maxAPI.post("Session archived and cleared for track: " + currentTrackName);
    } else {
        maxAPI.post("No active session to clear");
    }
    maxAPI.outlet("chatcleared");
});

maxAPI.addHandler("newchat", () => {
    if (currentTrackName) {
        currentSession = clearSession(currentTrackName);
        maxAPI.post("New session started for track: " + currentTrackName);
        maxAPI.outlet("newchat", currentSession.id);
    } else {
        maxAPI.post("Send a message first to establish track context");
        maxAPI.outlet("error", "No track context - send a message first");
    }
});

// =============================================================================
// READY
// =============================================================================

maxAPI.post("ChatM4L AI module ready");
