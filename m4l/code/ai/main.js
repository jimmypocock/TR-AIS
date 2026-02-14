/**
 * ChatM4L AI - node.script code for Max for Live
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
const fs = require("fs");
const path = require("path");
const os = require("os");

// Will be set dynamically
let anthropicClient = null;
let apiKey = "";

// Config file location: ~/Library/Application Support/ChatM4L/config.json
const CONFIG_DIR = path.join(os.homedir(), "Library", "Application Support", "ChatM4L");
const CONFIG_FILE = path.join(CONFIG_DIR, "config.json");

// System prompt for track-scoped AI
const SYSTEM_PROMPT = `You are ChatM4L, an AI assistant living on a single track in Ableton Live.
You can only control THIS track - its devices, parameters, and clips.
You receive context about the track's current state with each message.

IMPORTANT: You must respond with valid JSON only. No markdown, no explanation outside the JSON.

Response format:
{
  "thinking": "Your brief reasoning about what the user wants",
  "commands": [
    // Array of commands to execute (can be empty)
  ],
  "response": "What to tell the user (conversational, brief)"
}

Available commands:

1. Set a device parameter:
   { "action": "set_parameter", "device": 0, "param": 3, "value": 0.7 }
   - device: device index (from context)
   - param: parameter index (from context)
   - value: new value (check min/max in context)

2. Set track volume:
   { "action": "set_volume", "value": 0.8 }
   - value: 0.0 to 1.0

3. Set track pan:
   { "action": "set_pan", "value": 0.0 }
   - value: -1.0 (left) to 1.0 (right)

4. Mute/unmute track:
   { "action": "set_mute", "value": true }

5. Solo/unsolo track:
   { "action": "set_solo", "value": true }

6. Add MIDI notes to a clip:
   { "action": "add_notes", "clip_slot": 0, "length": 4, "notes": [
     { "pitch": 60, "start_time": 0, "duration": 0.5, "velocity": 100 }
   ]}
   - clip_slot: which slot (0-7 typically)
   - length: clip length in beats (if creating new clip)
   - notes: array of note objects
     - pitch: MIDI note (60 = C4)
     - start_time: in beats from clip start
     - duration: in beats
     - velocity: 1-127

7. Clear all notes from a clip:
   { "action": "clear_clip", "clip_slot": 0 }

8. Fire (play) a clip:
   { "action": "fire_clip", "clip_slot": 0 }

9. Stop a clip:
   { "action": "stop_clip", "clip_slot": 0 }

Guidelines:
- Look at the device parameters in context to find the right one to adjust
- For "warmer" sounds, typically reduce high frequencies or filter cutoff
- For "brighter" sounds, increase high frequencies or filter cutoff
- When adding notes, think musically - use appropriate scales and rhythms
- Keep responses brief and friendly
- If you can't do something, explain why

Remember: Only output valid JSON. No other text.`;

// =============================================================================
// CONFIG FILE MANAGEMENT
// =============================================================================

function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_FILE)) {
            const data = fs.readFileSync(CONFIG_FILE, "utf8");
            return JSON.parse(data);
        }
    } catch (e) {
        maxAPI.post("Error loading config: " + e.message);
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
        maxAPI.post("Config saved to: " + CONFIG_FILE);
        return true;
    } catch (e) {
        maxAPI.post("Error saving config: " + e.message);
        return false;
    }
}

function initializeClient(key) {
    try {
        const Anthropic = require("@anthropic-ai/sdk");
        anthropicClient = new Anthropic({ apiKey: key });
        apiKey = key;
        maxAPI.post("Anthropic client initialized");
        maxAPI.outlet("ready");
        return true;
    } catch (e) {
        maxAPI.post("Error initializing Anthropic client: " + e.message);
        return false;
    }
}

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
        // Save to config file for future instances
        const config = loadConfig();
        config.apiKey = key;
        if (saveConfig(config)) {
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

    if (!anthropicClient) {
        maxAPI.post("No client, sending error...");
        maxAPI.outlet("error", "API key not configured");
        maxAPI.post("Error sent");
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

        // Call Claude
        const response = await anthropicClient.messages.create({
            model: "claude-sonnet-4-20250514",
            max_tokens: 1024,
            system: SYSTEM_PROMPT,
            messages: [{
                role: "user",
                content: userContent
            }]
        });

        // Extract the text response
        const responseText = response.content[0].text;
        maxAPI.post("Raw response: " + responseText.substring(0, 100) + "...");

        // Parse the JSON response
        let result;
        try {
            // Try to extract JSON if there's extra text
            const jsonMatch = responseText.match(/\{[\s\S]*\}/);
            if (jsonMatch) {
                result = JSON.parse(jsonMatch[0]);
            } else {
                throw new Error("No JSON found in response");
            }
        } catch (parseError) {
            maxAPI.post("Parse error: " + parseError.message);
            // Return a safe fallback
            result = {
                thinking: "Had trouble parsing the response",
                commands: [],
                response: responseText.substring(0, 200)
            };
        }

        // Send back to Max
        maxAPI.outlet("response", JSON.stringify(result));

    } catch (e) {
        maxAPI.post("Error: " + e.message);
        maxAPI.outlet("error", e.message);
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
        hasApiKey: !!apiKey,
        hasClient: !!anthropicClient,
        configPath: CONFIG_FILE
    };
    maxAPI.post("Status: " + JSON.stringify(status));
});

// Handler to clear saved API key
maxAPI.addHandler("clearkey", () => {
    const config = loadConfig();
    delete config.apiKey;
    saveConfig(config);
    apiKey = "";
    anthropicClient = null;
    maxAPI.post("API key cleared from config");
    maxAPI.outlet("keycleared");
});

// =============================================================================
// READY
// =============================================================================

maxAPI.post("ChatM4L AI module ready");
if (!anthropicClient) {
    maxAPI.post("Waiting for API key...");
    maxAPI.post("Set once and it will auto-load for all future instances");
    // Tell bridge to show setup message
    maxAPI.outlet("needskey");
}
