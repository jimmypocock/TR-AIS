/**
 * ChatM4L AI - node.script entry point for Max for Live
 *
 * This script runs in the node.script object and handles:
 * - Claude API calls
 * - Message processing
 * - Command generation
 *
 * Communication with Max:
 *   Input: Messages from bridge.js (v8 object)
 *   Output: Responses via maxAPI.outlet()
 */

const maxAPI = require("max-api");

// Import modules
const { loadConfig, saveConfig, CONFIG_FILE } = require("./config");
const { initializeClient, getClient, clearClient, isReady } = require("./client");
const { addMessage, getMessages, clear: clearConversation, getLength } = require("./conversation");
const { SYSTEM_PROMPT } = require("./prompt");

// =============================================================================
// INITIALIZATION
// =============================================================================

maxAPI.post("ChatM4L AI module loading...");

// Try to load API key from config on startup
const config = loadConfig();
if (config.apiKey) {
    maxAPI.post("Found saved API key, initializing...");
    if (initializeClient(config.apiKey)) {
        maxAPI.post("Auto-loaded API key from config");
        maxAPI.outlet("ready");
    }
} else {
    maxAPI.post("No saved API key found");
}

// =============================================================================
// API KEY HANDLING
// =============================================================================

maxAPI.addHandler("apikey", async (key) => {
    maxAPI.post("API key received");

    // Validate key isn't empty
    if (!key || key.trim() === "") {
        maxAPI.outlet("error", "API key cannot be empty");
        return;
    }

    if (initializeClient(key)) {
        maxAPI.post("Anthropic client initialized");
        maxAPI.outlet("ready");

        // Save to config file for future instances
        const config = loadConfig();
        config.apiKey = key;
        if (saveConfig(config)) {
            maxAPI.post("Config saved to: " + CONFIG_FILE);
            maxAPI.post("API key saved - will auto-load next time");

            // Verify it was saved correctly
            const verifyConfig = loadConfig();
            if (verifyConfig.apiKey === key) {
                maxAPI.outlet("keysaved");
            } else {
                maxAPI.outlet("error", "Failed to verify saved key");
            }
        } else {
            maxAPI.outlet("error", "Failed to save API key");
        }
    } else {
        maxAPI.outlet("error", "Failed to initialize AI");
    }
});

// =============================================================================
// CHAT HANDLING
// =============================================================================

maxAPI.addHandler("chat", async (payloadJson) => {
    maxAPI.post("Chat handler called");

    if (!isReady()) {
        maxAPI.post("No client, sending error...");
        maxAPI.outlet("error", "API key not configured");
        return;
    }

    try {
        const payload = JSON.parse(payloadJson);
        const { message, context } = payload;

        maxAPI.post("Processing: " + message);

        // Build the user message with context
        const userContent = `Current track state:
${JSON.stringify(context, null, 2)}

User request: ${message}`;

        // Add user message to conversation history
        addMessage("user", userContent);

        // Get full conversation history for Claude
        const messages = getMessages();

        maxAPI.post("Sending " + messages.length + " messages to Claude");

        // Call Claude with full conversation history
        const response = await getClient().messages.create({
            model: "claude-sonnet-4-20250514",
            max_tokens: 1024,
            system: SYSTEM_PROMPT,
            messages: messages
        });

        // Extract the text response
        const responseText = response.content[0].text;
        maxAPI.post("Raw response: " + responseText.substring(0, 100) + "...");

        // Add assistant response to conversation history
        addMessage("assistant", responseText);

        // Parse the JSON response
        let result;
        try {
            // Try to parse the whole response first (ideal case)
            result = JSON.parse(responseText);
        } catch (directParseError) {
            // Fallback: extract JSON block if there's extra text
            try {
                const jsonMatch = responseText.match(/\{[\s\S]*\}/);
                if (jsonMatch) {
                    result = JSON.parse(jsonMatch[0]);
                } else {
                    throw new Error("No JSON found in response");
                }
            } catch (extractError) {
                maxAPI.post("Parse error: " + extractError.message);
                // Return a safe fallback
                result = {
                    thinking: "Had trouble parsing the response",
                    commands: [],
                    response: responseText.substring(0, 200)
                };
            }
        }

        // Send back to Max
        maxAPI.outlet("response", JSON.stringify(result));

    } catch (e) {
        maxAPI.post("Error: " + e.message);

        // Provide user-friendly error messages
        let userMessage;
        const errorLower = e.message.toLowerCase();

        if (errorLower.includes("401") || errorLower.includes("invalid") || errorLower.includes("authentication")) {
            userMessage = "Invalid API key - please check your key in settings";
        } else if (errorLower.includes("429") || errorLower.includes("rate")) {
            userMessage = "Rate limited - please wait a moment and try again";
        } else if (errorLower.includes("network") || errorLower.includes("fetch") || errorLower.includes("connect")) {
            userMessage = "Network error - check your internet connection";
        } else if (errorLower.includes("timeout")) {
            userMessage = "Request timed out - try again";
        } else {
            userMessage = "Something went wrong - try again";
        }

        maxAPI.outlet("error", userMessage);
    }
});

// =============================================================================
// UTILITY HANDLERS
// =============================================================================

maxAPI.addHandler("ping", () => {
    maxAPI.outlet("pong");
    maxAPI.post("Pong!");
});

maxAPI.addHandler("status", () => {
    const status = {
        hasApiKey: isReady(),
        configPath: CONFIG_FILE,
        conversationLength: getLength()
    };
    maxAPI.post("Status: " + JSON.stringify(status));
});

// Handler to clear saved API key
maxAPI.addHandler("clearkey", () => {
    const config = loadConfig();
    delete config.apiKey;
    saveConfig(config);
    clearClient();
    maxAPI.post("API key cleared from config");
    maxAPI.outlet("keycleared");
});

// Handler to clear conversation history
maxAPI.addHandler("clearchat", () => {
    clearConversation();
    maxAPI.post("Conversation history cleared");
    maxAPI.outlet("chatcleared");
});

// =============================================================================
// READY
// =============================================================================

maxAPI.post("ChatM4L AI module ready");
if (!isReady()) {
    maxAPI.post("Waiting for API key...");
    maxAPI.post("Set once and it will auto-load for all future instances");
    // Tell bridge to show setup message
    maxAPI.outlet("needskey");
}
