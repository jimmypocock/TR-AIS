/**
 * ChatM4L Bridge - v8 object code for Max for Live
 *
 * This script runs in the v8 object and bridges between:
 * - The jsui (chat-ui.js) - complete UI component
 * - The Live API (track, devices, clips)
 * - The node.script (Claude AI)
 *
 * Inlets:
 *   0: Messages from jsui and node.script
 *
 * Outlets:
 *   0: To node.script (chat messages + context)
 *   1: To jsui (chat-ui.js) - messages
 */

// Max boilerplate
inlets = 1;
outlets = 2;

// Outlet indices
const OUT_NODE = 0;      // To node.script
const OUT_CHAT = 1;      // To jsui chat-ui.js

// =============================================================================
// STATE
// =============================================================================

let currentView = "chat";  // chat | settings | skills | profile | help
let pendingInput = "";     // Stored input text from textedit
let nodeStatus = {
    ready: false,
    provider: "unknown",
    model: "unknown",
    activeSkill: null,
    skills: []
};

// =============================================================================
// INITIALIZATION
// =============================================================================

function bang() {
    post("ChatM4L Bridge initialized\n");

    // Check if Live API is available
    const track = new LiveAPI("this_device canonical_parent");
    if (!track.id) {
        post("Live API not ready (this is normal during save)\n");
        return;
    }

    const context = getTrackContext();
    post("Track: " + context.name + "\n");

    // Trigger jsui redraw
    outlet(OUT_CHAT, "bang");
}

// =============================================================================
// VIEW MANAGEMENT (jsui handles UI, we just track state)
// =============================================================================

/**
 * Called from jsui when view changes
 * @param {string} viewName - The new view name
 */
function view(viewName) {
    const validViews = ["chat", "settings", "skills", "profile", "help"];
    if (validViews.indexOf(viewName) === -1) {
        post("Invalid view: " + viewName + "\n");
        return;
    }

    currentView = viewName;
    post("View: " + viewName + "\n");
}

/**
 * Called from jsui when send button is clicked
 * The textedit should send its content via "input" message
 */
function send() {
    if (pendingInput && pendingInput.trim() !== "") {
        chat(pendingInput);
        pendingInput = "";
    } else {
        post("No input to send\n");
    }
}

/**
 * Receive text from the textedit input
 * Called when textedit outputs on return (Enter key)
 * Immediately sends the message
 */
function input() {
    var args = Array.prototype.slice.call(arguments);
    var message = args.join(" ");
    if (message && message.trim() !== "") {
        chat(message);
    }
}

/**
 * Handle "text" message from textedit
 * textedit sends: text <content>
 */
function text() {
    post("text() called with " + arguments.length + " args\n");
    for (var i = 0; i < arguments.length; i++) {
        post("  arg[" + i + "] = " + arguments[i] + " (type: " + typeof arguments[i] + ")\n");
    }

    var args = Array.prototype.slice.call(arguments);
    var message = args.join(" ");
    post("text() message: " + message + "\n");

    if (message && message.trim() !== "" && message !== "0") {
        chat(message);
    }
}

/**
 * Store pending input for send button (if textedit sends on keyup instead)
 */
function setInput() {
    var args = Array.prototype.slice.call(arguments);
    pendingInput = args.join(" ");
}

// =============================================================================
// CHAT HANDLING
// =============================================================================

function chat(userMessage) {
    if (!userMessage || userMessage.trim() === "") {
        return;
    }

    // Switch to chat view if not already (tell jsui)
    if (currentView !== "chat") {
        outlet(OUT_CHAT, "setView", "chat");
        currentView = "chat";
    }

    // Add user message to display
    addToHistory("You", userMessage);

    // Show thinking indicator
    outlet(OUT_CHAT, "thinking", 1);

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
    // Hide thinking indicator
    outlet(OUT_CHAT, "thinking", 0);

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

    } catch (e) {
        post("Error parsing response: " + e + "\n");
        addToHistory("System", "Error: Could not parse AI response");
    }
}

function error() {
    // Hide thinking indicator
    outlet(OUT_CHAT, "thinking", 0);

    var message = Array.prototype.slice.call(arguments).join(" ");
    post("AI Error: " + message + "\n");
    addToHistory("System", "Error: " + message);
}

// =============================================================================
// NODE.SCRIPT STATUS HANDLERS
// =============================================================================

function ready() {
    nodeStatus.ready = true;
    post("AI ready\n");
    // Trigger jsui redraw
    outlet(OUT_CHAT, "bang");
}

function needsconfig() {
    nodeStatus.ready = false;
    post("Config needed\n");
    addToHistory("System", "Welcome! Run /createconfig to get started.");
}

function status(jsonString) {
    // Called when node.script sends status update
    try {
        const data = JSON.parse(jsonString);
        nodeStatus.provider = data.provider || "unknown";
        nodeStatus.model = data.model || "unknown";
        nodeStatus.activeSkill = data.activeSkill || null;
        nodeStatus.skills = data.availableSkills || [];
        nodeStatus.ready = data.ready || false;
        post("Status updated: " + nodeStatus.provider + "/" + nodeStatus.model + "\n");

        // TODO: Could pass status to jsui for dynamic settings/skills display
        // For now, jsui shows static content
    } catch (e) {
        post("Error parsing status: " + e + "\n");
    }
}

// =============================================================================
// TRACK CONTEXT
// =============================================================================

function getTrackContext() {
    const track = new LiveAPI("this_device canonical_parent");

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

    const count = Math.floor(deviceIds.length / 2);

    for (let i = 0; i < count; i++) {
        const device = new LiveAPI("this_device canonical_parent devices " + i);
        const name = device.get("name").toString();
        const className = device.get("class_name").toString();

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

    if (slot.get("has_clip") == 0) {
        slot.call("create_clip", length);
        post("Created clip in slot " + clipSlotIndex + "\n");
    }

    const clip = new LiveAPI("this_device canonical_parent clip_slots " + clipSlotIndex + " clip");
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
    // Send message to jsui chat display
    // jsui's anything() handler will receive this as: sender(message)
    outlet(OUT_CHAT, sender, message);
}

function clearHistory() {
    // Clear jsui chat display
    outlet(OUT_CHAT, "clear");
    post("Chat history cleared\n");
}

/**
 * Called from node.script when chat is cleared
 */
function chatcleared() {
    clearHistory();
}

/**
 * Called from node.script when new chat is created
 */
function newchat(sessionId) {
    clearHistory();
    post("New chat session: " + sessionId + "\n");
}

/**
 * Receive inputrect from jsui (for positioning textedit)
 * This is informational - textedit position is set manually in Max
 */
function inputrect(x, y, w, h) {
    post("Input rect: " + x + ", " + y + ", " + w + ", " + h + "\n");
}

/**
 * Catch stdout from node.script (console.log output)
 */
function stdout() {
    // Ignore stdout messages from node.script
}

/**
 * Catch any unhandled messages - treat as chat input
 */
function anything() {
    var name = messagename;
    var args = Array.prototype.slice.call(arguments);

    // Combine messagename + args as the full message
    // This handles textedit output which sends raw text
    var fullMessage = name;
    if (args.length > 0) {
        fullMessage += " " + args.join(" ");
    }

    // Ignore internal Max messages
    if (name === "script" || name === "compile" || name === "loadbang") {
        return;
    }

    post("Chat input: " + fullMessage + "\n");
    chat(fullMessage);
}

// =============================================================================
// DEBUG HELPERS
// =============================================================================

function dumpContext() {
    const context = getTrackContext();
    post("--- Track Context ---\n");
    post(JSON.stringify(context, null, 2) + "\n");
    post("---------------------\n");
}

function testNote() {
    addMidiNotes(0, [
        { pitch: 60, start_time: 0, duration: 0.5, velocity: 100 },
        { pitch: 64, start_time: 0.5, duration: 0.5, velocity: 100 },
        { pitch: 67, start_time: 1, duration: 0.5, velocity: 100 },
        { pitch: 72, start_time: 1.5, duration: 0.5, velocity: 100 }
    ], 4);
}
