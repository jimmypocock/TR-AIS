/**
 * ChatM4L Bridge - v8 object code for Max for Live
 *
 * This script runs in the v8 object and bridges between:
 * - The Max UI (jsui chat display, buttons, panels)
 * - The Live API (track, devices, clips)
 * - The node.script (Claude AI)
 *
 * Inlets:
 *   0: Messages from UI and node.script
 *
 * Outlets:
 *   0: To node.script (chat messages + context)
 *   1: To chat display (jsui) - message commands
 *   2: To static content display (textedit) - for non-chat views
 *   3: To sidebar button states
 *   4: To input field visibility/state
 */

// Max boilerplate
inlets = 1;
outlets = 5;

// Outlet indices
const OUT_NODE = 0;      // To node.script
const OUT_CHAT = 1;      // To jsui chat display
const OUT_STATIC = 2;    // To textedit for static views (settings, help, etc)
const OUT_SIDEBAR = 3;   // To sidebar (active button index)
const OUT_INPUT = 4;     // To input area (show/hide, enable/disable)

// =============================================================================
// STATE
// =============================================================================

let currentView = "chat";  // chat | settings | skills | profile | help
let chatHistory = [];
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

    // Show chat view by default
    setView("chat");
}

// =============================================================================
// VIEW MANAGEMENT
// =============================================================================

function setView(viewName) {
    const validViews = ["chat", "settings", "skills", "profile", "help"];
    if (validViews.indexOf(viewName) === -1) {
        post("Invalid view: " + viewName + "\n");
        return;
    }

    currentView = viewName;
    post("View changed to: " + viewName + "\n");

    // Update sidebar highlight (0=settings, 1=skills, 2=profile, 3=help)
    const sidebarIndex = {
        "settings": 0,
        "skills": 1,
        "profile": 2,
        "help": 3,
        "chat": -1  // No sidebar button for chat
    };
    outlet(OUT_SIDEBAR, sidebarIndex[viewName]);

    // Show/hide input based on view
    outlet(OUT_INPUT, viewName === "chat" ? 1 : 0);

    // Toggle visibility between chat jsui and static textedit
    // chat view: show jsui (1), hide textedit (0)
    // other views: hide jsui (0), show textedit (1)
    outlet(OUT_CHAT, "visible", viewName === "chat" ? 1 : 0);
    outlet(OUT_STATIC, "visible", viewName === "chat" ? 0 : 1);

    // Refresh content
    refreshView();
}

function refreshView() {
    if (currentView === "chat") {
        // Chat view uses jsui - just trigger a redraw
        // Messages are already in the jsui, no need to resend
        outlet(OUT_CHAT, "bang");
        return;
    }

    // Other views use static textedit
    let content = "";

    switch (currentView) {
        case "settings":
            content = getSettingsContent();
            break;
        case "skills":
            content = getSkillsContent();
            break;
        case "profile":
            content = getProfileContent();
            break;
        case "help":
            content = getHelpContent();
            break;
    }

    outlet(OUT_STATIC, "set", content);
}

// Note: Chat content is managed by jsui (chat-display.js)
// getChatContent() removed - jsui handles its own state

function getSettingsContent() {
    let content = "SETTINGS\n";
    content += "─────────────────────────\n\n";
    content += "Provider: " + nodeStatus.provider + "\n";
    content += "Model: " + nodeStatus.model + "\n\n";
    content += "Status: " + (nodeStatus.ready ? "Ready" : "Not configured") + "\n\n";
    content += "─────────────────────────\n\n";
    content += "Config location:\n";
    content += "~/Library/Application Support/ChatM4L/\n\n";
    content += "Commands:\n";
    content += "• /reload - Reload config\n";
    content += "• /openconfig - Show config path\n";
    content += "• /createconfig - Create/reset config";
    return content;
}

function getSkillsContent() {
    let content = "SKILLS\n";
    content += "─────────────────────────\n\n";

    if (nodeStatus.skills.length === 0) {
        content += "No skills available.\n\n";
        content += "Add skills to:\n";
        content += "~/Library/Application Support/ChatM4L/skills/";
    } else {
        content += "Available skills:\n\n";
        for (var i = 0; i < nodeStatus.skills.length; i++) {
            var skill = nodeStatus.skills[i];
            var isActive = nodeStatus.activeSkill === skill;
            content += (isActive ? "● " : "○ ") + skill;
            if (isActive) content += "  [Active]";
            content += "\n";
        }
        content += "\n─────────────────────────\n\n";
        content += "Commands:\n";
        content += "• /<skill> - Activate skill\n";
        content += "• /skill off - Deactivate";
    }
    return content;
}

function getProfileContent() {
    let content = "PROFILE\n";
    content += "─────────────────────────\n\n";
    content += "Your user profile helps ChatM4L\n";
    content += "understand your musical style.\n\n";
    content += "Edit: core/user.md\n\n";
    content += "─────────────────────────\n\n";
    content += "Include:\n";
    content += "• Genres & influences\n";
    content += "• Reference artists\n";
    content += "• Sound preferences\n";
    content += "• Hardware & plugins";
    return content;
}

function getHelpContent() {
    let content = "HELP\n";
    content += "─────────────────────────\n\n";
    content += "COMMANDS\n\n";
    content += "/help      Show this help\n";
    content += "/status    Show status\n";
    content += "/newchat   Clear conversation\n";
    content += "/reload    Reload config\n";
    content += "/skills    List skills\n";
    content += "/<skill>   Activate skill\n\n";
    content += "─────────────────────────\n\n";
    content += "TIPS\n\n";
    content += "• Just type naturally!\n";
    content += "• AI sees your track context\n";
    content += "• Use skills for specialized help";
    return content;
}

// =============================================================================
// CHAT HANDLING
// =============================================================================

function chat(userMessage) {
    if (!userMessage || userMessage.trim() === "") {
        return;
    }

    // Switch to chat view if not already
    if (currentView !== "chat") {
        setView("chat");
    }

    // Add user message to history
    addToHistory("You", userMessage);

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
    refreshView();
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

        // Refresh if viewing settings or skills
        if (currentView === "settings" || currentView === "skills") {
            refreshView();
        }
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
    // Format: message <sender> <text>
    outlet(OUT_CHAT, "message", sender, message);

    // Also keep local history for potential future use
    const entry = sender + ": " + message;
    chatHistory.push(entry);

    if (chatHistory.length > 50) {
        chatHistory.shift();
    }
}

function clearHistory() {
    chatHistory = [];
    // Clear jsui chat display
    outlet(OUT_CHAT, "clear");
    post("Chat history cleared\n");
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
