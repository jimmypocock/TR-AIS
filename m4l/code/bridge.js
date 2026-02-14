/**
 * ChatM4L Bridge - v8 object code for Max for Live
 *
 * This script runs in the v8 object and bridges between:
 * - The Max UI (textedit, buttons)
 * - The Live API (track, devices, clips)
 * - The node.script (Claude AI)
 *
 * Inlets:
 *   0: Messages from UI and node.script
 *
 * Outlets:
 *   0: To node.script (chat messages + context)
 *   1: To chat history display
 *   2: To status display
 */

// Max boilerplate
inlets = 1;
outlets = 2;

// Outlet indices
const OUT_NODE = 0;      // To node.script
const OUT_HISTORY = 1;   // To chat history textedit

// Chat history buffer
let chatHistory = [];

// API key storage
let apiKey = "";

// =============================================================================
// INITIALIZATION
// =============================================================================

function bang() {
    // Called when device loads (triggered by live.thisdevice)
    post("ChatM4L Bridge initialized\n");
    updateStatus("Ready");

    // Get initial track context to verify we're working
    // Check if Live API is available (won't be during save)
    const track = new LiveAPI("this_device canonical_parent");
    if (!track.id) {
        post("Live API not ready (this is normal during save)\n");
        return;
    }

    const context = getTrackContext();
    post("Track: " + context.name + "\n");
    post("Devices: " + context.devices.length + "\n");
}

// =============================================================================
// API KEY MANAGEMENT
// =============================================================================

function setApiKey(key) {
    apiKey = key;
    // Send to node.script (it will save to config file)
    outlet(OUT_NODE, "apikey", key);
    updateStatus("Saving key...");
    post("API key sent to node.script\n");
}

function getApiKey() {
    return apiKey;
}

// =============================================================================
// CHAT HANDLING
// =============================================================================

function chat(userMessage) {
    // Called when user submits a message
    if (!userMessage || userMessage.trim() === "") {
        return;
    }

    // Note: apiKey may be auto-loaded in node.script from config
    // So we check if node.script is ready by trying to send

    // Add user message to history
    addToHistory("You", userMessage);
    updateStatus("Thinking...");

    // Get current track context
    const context = getTrackContext();

    // Send to node.script
    const payload = {
        message: userMessage,
        context: context
    };

    outlet(OUT_NODE, "chat", JSON.stringify(payload));
}

function response(jsonString) {
    // Called when node.script returns a response
    try {
        const result = JSON.parse(jsonString);

        // Execute any commands
        if (result.commands && Array.isArray(result.commands)) {
            for (const cmd of result.commands) {
                executeCommand(cmd);
            }
        }

        // Add AI response to history
        if (result.response) {
            addToHistory("AI", result.response);
        }

        updateStatus("Ready");

    } catch (e) {
        post("Error parsing response: " + e + "\n");
        addToHistory("System", "Error: Could not parse AI response");
        updateStatus("Error");
    }
}

function error() {
    // Called when node.script reports an error
    // Arguments may be split by spaces, so rejoin them
    var message = Array.prototype.slice.call(arguments).join(" ");
    post("AI Error: " + message + "\n");

    // Give helpful message for common errors
    if (message === "API key not configured") {
        addToHistory("System", "No API key set. Please click Settings (⚙) to configure.");
        updateStatus("Setup Required");
    } else {
        addToHistory("System", "Error: " + message);
        updateStatus("Error");
    }
}

function ready() {
    // Called when node.script has a valid API key (auto-loaded or just set)
    post("AI ready with API key\n");
    updateStatus("Ready");
}

function keycleared() {
    // Called when API key is cleared from config
    post("API key cleared\n");
    updateStatus("No API Key");
    addToHistory("System", "API key cleared. Enter a new key to continue.");
}

function needskey() {
    // Called when node.script starts without a saved API key
    post("No API key configured\n");
    updateStatus("Setup Required");
    addToHistory("System", "Welcome! Please click Settings (⚙) to enter your Anthropic API key.");
}

function keysaved() {
    // Called when API key is successfully saved and verified
    post("API key saved and verified\n");
    addToHistory("System", "API Key Saved!");
}

// =============================================================================
// TRACK CONTEXT
// =============================================================================

function getTrackContext() {
    const track = new LiveAPI("this_device canonical_parent");

    // Return empty context if Live API not available
    if (!track.id) {
        return {
            name: "Unknown",
            color: 0,
            volume: 0,
            pan: 0,
            muted: false,
            soloed: false,
            armed: false,
            devices: [],
            clipSlots: []
        };
    }

    const context = {
        name: track.get("name").toString(),
        color: track.get("color"),
        volume: getTrackVolume(),
        pan: getTrackPan(),
        muted: track.get("mute") == 1,
        soloed: track.get("solo") == 1,
        armed: track.get("arm") == 1,
        devices: getDevices(),
        clipSlots: getClipSlots()
    };

    return context;
}

function getTrackVolume() {
    const mixer = new LiveAPI("this_device canonical_parent mixer_device volume");
    return mixer.get("value");
}

function getTrackPan() {
    const mixer = new LiveAPI("this_device canonical_parent mixer_device panning");
    return mixer.get("value");
}

function getDevices() {
    const track = new LiveAPI("this_device canonical_parent");
    const deviceIds = track.get("devices");
    const devices = [];

    // deviceIds comes as [id, id, id, ...] - get count
    const count = Math.floor(deviceIds.length / 2);

    for (let i = 0; i < count; i++) {
        const device = new LiveAPI("this_device canonical_parent devices " + i);
        const name = device.get("name").toString();
        const className = device.get("class_name").toString();

        // Skip our own device
        if (className === "MaxForLive" || name === "ChatM4L") {
            continue;
        }

        devices.push({
            index: i,
            name: name,
            class: className,
            parameters: getDeviceParameters(i)
        });
    }

    return devices;
}

function getDeviceParameters(deviceIndex) {
    const device = new LiveAPI("this_device canonical_parent devices " + deviceIndex);
    const paramIds = device.get("parameters");
    const params = [];

    const count = Math.floor(paramIds.length / 2);
    // Limit to first 20 params to avoid huge context
    const limit = Math.min(count, 20);

    for (let i = 0; i < limit; i++) {
        const param = new LiveAPI(
            "this_device canonical_parent devices " + deviceIndex + " parameters " + i
        );

        params.push({
            index: i,
            name: param.get("name").toString(),
            value: param.get("value"),
            min: param.get("min"),
            max: param.get("max")
        });
    }

    return params;
}

function getClipSlots() {
    const track = new LiveAPI("this_device canonical_parent");
    const slotIds = track.get("clip_slots");
    const slots = [];

    const count = Math.floor(slotIds.length / 2);
    // Limit to first 8 slots (one scene page)
    const limit = Math.min(count, 8);

    for (let i = 0; i < limit; i++) {
        const slot = new LiveAPI("this_device canonical_parent clip_slots " + i);
        const hasClip = slot.get("has_clip") == 1;

        const slotInfo = {
            index: i,
            hasClip: hasClip
        };

        if (hasClip) {
            const clip = new LiveAPI("this_device canonical_parent clip_slots " + i + " clip");
            slotInfo.clipName = clip.get("name").toString();
            slotInfo.clipLength = clip.get("length");
            slotInfo.isPlaying = clip.get("is_playing") == 1;
        }

        slots.push(slotInfo);
    }

    return slots;
}

// =============================================================================
// COMMAND EXECUTION
// =============================================================================

function executeCommand(cmd) {
    post("Executing: " + cmd.action + "\n");

    try {
        switch (cmd.action) {
            case "set_parameter":
                setDeviceParameter(cmd.device, cmd.param, cmd.value);
                break;

            case "set_volume":
                setTrackVolume(cmd.value);
                break;

            case "set_pan":
                setTrackPan(cmd.value);
                break;

            case "set_mute":
                setTrackMute(cmd.value);
                break;

            case "set_solo":
                setTrackSolo(cmd.value);
                break;

            case "add_notes":
                addMidiNotes(cmd.clip_slot, cmd.notes, cmd.length || 4);
                break;

            case "clear_clip":
                clearClip(cmd.clip_slot);
                break;

            case "fire_clip":
                fireClip(cmd.clip_slot);
                break;

            case "stop_clip":
                stopClip(cmd.clip_slot);
                break;

            default:
                post("Unknown command: " + cmd.action + "\n");
        }
    } catch (e) {
        post("Command error: " + e + "\n");
    }
}

function setDeviceParameter(deviceIndex, paramIndex, value) {
    const param = new LiveAPI(
        "this_device canonical_parent devices " + deviceIndex + " parameters " + paramIndex
    );
    param.set("value", value);
    post("Set device " + deviceIndex + " param " + paramIndex + " to " + value + "\n");
}

function setTrackVolume(value) {
    const volume = new LiveAPI("this_device canonical_parent mixer_device volume");
    volume.set("value", value);
    post("Set volume to " + value + "\n");
}

function setTrackPan(value) {
    const pan = new LiveAPI("this_device canonical_parent mixer_device panning");
    pan.set("value", value);
    post("Set pan to " + value + "\n");
}

function setTrackMute(value) {
    const track = new LiveAPI("this_device canonical_parent");
    track.set("mute", value ? 1 : 0);
    post("Set mute to " + value + "\n");
}

function setTrackSolo(value) {
    const track = new LiveAPI("this_device canonical_parent");
    track.set("solo", value ? 1 : 0);
    post("Set solo to " + value + "\n");
}

function addMidiNotes(clipSlotIndex, notes, length) {
    const slot = new LiveAPI("this_device canonical_parent clip_slots " + clipSlotIndex);

    // Create clip if needed
    if (slot.get("has_clip") == 0) {
        slot.call("create_clip", length);
        post("Created clip in slot " + clipSlotIndex + "\n");
    }

    const clip = new LiveAPI("this_device canonical_parent clip_slots " + clipSlotIndex + " clip");

    // Add notes
    clip.call("add_new_notes", { notes: notes });
    post("Added " + notes.length + " notes to clip\n");
}

function clearClip(clipSlotIndex) {
    const slot = new LiveAPI("this_device canonical_parent clip_slots " + clipSlotIndex);

    if (slot.get("has_clip") == 1) {
        const clip = new LiveAPI("this_device canonical_parent clip_slots " + clipSlotIndex + " clip");
        const length = clip.get("length");
        clip.call("remove_notes_extended", 0, 128, 0, length);
        post("Cleared clip in slot " + clipSlotIndex + "\n");
    }
}

function fireClip(clipSlotIndex) {
    const slot = new LiveAPI("this_device canonical_parent clip_slots " + clipSlotIndex);
    slot.call("fire");
    post("Fired clip in slot " + clipSlotIndex + "\n");
}

function stopClip(clipSlotIndex) {
    const slot = new LiveAPI("this_device canonical_parent clip_slots " + clipSlotIndex);
    slot.call("stop");
    post("Stopped clip in slot " + clipSlotIndex + "\n");
}

// =============================================================================
// UI HELPERS
// =============================================================================

function addToHistory(sender, message) {
    const entry = sender + ": " + message;
    chatHistory.push(entry);

    // Keep last 50 messages
    if (chatHistory.length > 50) {
        chatHistory.shift();
    }

    // Send to history display
    outlet(OUT_HISTORY, "set", chatHistory.join("\n"));
}

function updateStatus(status) {
    // Show status in chat history (skip "Ready" to reduce noise)
    if (status !== "Ready") {
        addToHistory("System", status);
    }
}

function clearHistory() {
    chatHistory = [];
    outlet(OUT_HISTORY, "set", "");
    post("Chat history cleared\n");
}

// =============================================================================
// DEBUG HELPERS
// =============================================================================

function dumpContext() {
    // Debug function to print current context
    const context = getTrackContext();
    post("--- Track Context ---\n");
    post(JSON.stringify(context, null, 2) + "\n");
    post("---------------------\n");
}

function testNote() {
    // Debug function to add a test note
    addMidiNotes(0, [
        { pitch: 60, start_time: 0, duration: 0.5, velocity: 100 },
        { pitch: 64, start_time: 0.5, duration: 0.5, velocity: 100 },
        { pitch: 67, start_time: 1, duration: 0.5, velocity: 100 },
        { pitch: 72, start_time: 1.5, duration: 0.5, velocity: 100 }
    ], 4);
}
