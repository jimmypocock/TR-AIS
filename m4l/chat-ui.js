/**
 * ChatM4L UI - Complete jsui interface for Max for Live
 *
 * A self-contained UI component that handles:
 * - Chat display with alternating colors
 * - Input area with > prompt
 * - Send button
 * - Sidebar navigation buttons
 *
 * Usage in Max:
 *   [jsui @filename chat-ui.js @size 450 350]
 *
 * You only need to position:
 *   1. This jsui
 *   2. A textedit for text input (positioned over the input area)
 *
 * Inlets:
 *   0: Messages from bridge.js
 *
 * Outlets:
 *   0: To bridge.js (button clicks, etc.)
 */

// =============================================================================
// JSUI SETUP
// =============================================================================

autowatch = 1;
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 1;

// =============================================================================
// LAYOUT CONFIGURATION
// =============================================================================

// Ableton M4L device height is FIXED at 169 pixels!
// Width is adjustable. We'll use 500px wide.
var DEVICE_HEIGHT = 169;
var DEVICE_WIDTH = 500;

var layout = {
    sidebar: {
        width: 40,
        buttonHeight: 42,  // 4 buttons × 42px = 168px (fits in 169px)
        buttons: [
            { id: "settings", icon: "S", label: "Settings" },
            { id: "skills", icon: "K", label: "Skills" },
            { id: "profile", icon: "P", label: "Profile" },
            { id: "help", icon: "?", label: "Help" }
        ]
    },
    input: {
        height: 36,
        promptWidth: 20,
        sendButtonWidth: 40
    }
};

// =============================================================================
// COLORS (Ableton-style)
// =============================================================================

var colors = {
    // Backgrounds
    bgPrimary:   [0.239, 0.239, 0.239, 1],    // #3D3D3D - main bg
    bgSecondary: [0.196, 0.196, 0.196, 1],    // #323232 - alt rows
    bgInput:     [0.102, 0.102, 0.102, 1],    // #1A1A1A - input area
    bgSidebar:   [0.180, 0.180, 0.180, 1],    // #2E2E2E - sidebar
    bgButton:    [0.220, 0.220, 0.220, 1],    // button normal
    bgButtonHover: [0.280, 0.280, 0.280, 1],  // button hover
    bgButtonActive: [0.961, 0.651, 0.137, 1], // button active (orange)

    // Text
    textPrimary:   [1, 1, 1, 1],              // #FFFFFF
    textSecondary: [0.702, 0.702, 0.702, 1],  // #B3B3B3
    textMuted:     [0.502, 0.502, 0.502, 1],  // #808080

    // Accents
    accentOrange: [0.961, 0.651, 0.137, 1],   // #F5A623
    accentBlue:   [0.314, 0.784, 1, 1],       // #50C8FF

    // Message backgrounds
    userBg:    [0.165, 0.165, 0.165, 1],
    aiBg:      [0.220, 0.220, 0.220, 1],
    systemBg:  [0.180, 0.180, 0.180, 1],
    errorBg:   [0.3, 0.15, 0.15, 1],

    // Dividers
    divider: [0.165, 0.165, 0.165, 1]         // #2A2A2A
};

// =============================================================================
// STATE
// =============================================================================

var messages = [];
var scrollOffset = 0;
var totalHeight = 0;

var currentView = "chat";  // chat | settings | skills | profile | help
var activeButton = -1;     // -1 = chat (no button), 0-3 = sidebar buttons
var hoveredButton = -1;
var hoveredSend = false;

var isThinking = false;    // Show thinking indicator

var viewWidth = 0;
var viewHeight = 0;

// Calculated areas (set in paint)
var chatArea = { x: 0, y: 0, w: 0, h: 0 };
var inputArea = { x: 0, y: 0, w: 0, h: 0 };
var sidebarArea = { x: 0, y: 0, w: 0, h: 0 };
var sendButtonArea = { x: 0, y: 0, w: 0, h: 0 };
var inputTextArea = { x: 0, y: 0, w: 0, h: 0 };  // Where textedit should go

// =============================================================================
// CONFIGURATION
// =============================================================================

var config = {
    fontName: "Ableton Sans Medium",
    fontSize: 12,
    lineHeight: 18,
    padding: { x: 10, y: 6 },
    messagePadding: 8,
    messageGap: 2,
    scrollSpeed: 40
};

// =============================================================================
// MAIN PAINT FUNCTION
// =============================================================================

function paint() {
    viewWidth = mgraphics.size[0];
    viewHeight = mgraphics.size[1];

    // Calculate layout areas
    calculateAreas();

    // Draw components (order matters - later draws cover earlier)
    drawChatArea();      // Draw chat first
    drawInputArea();     // Input covers any chat overspill
    drawSidebar();       // Sidebar on top
}

function calculateAreas() {
    var sw = layout.sidebar.width;
    var ih = layout.input.height;

    // Sidebar on right
    sidebarArea = {
        x: viewWidth - sw,
        y: 0,
        w: sw,
        h: viewHeight
    };

    // Input area at bottom (left of sidebar)
    inputArea = {
        x: 0,
        y: viewHeight - ih,
        w: viewWidth - sw,
        h: ih
    };

    // Send button in input area (right side)
    sendButtonArea = {
        x: inputArea.x + inputArea.w - layout.input.sendButtonWidth,
        y: inputArea.y,
        w: layout.input.sendButtonWidth,
        h: ih
    };

    // Text input area (where external textedit should be placed)
    inputTextArea = {
        x: inputArea.x + layout.input.promptWidth,
        y: inputArea.y + 8,
        w: inputArea.w - layout.input.promptWidth - layout.input.sendButtonWidth - 10,
        h: ih - 16
    };

    // Chat area (main content)
    chatArea = {
        x: 0,
        y: 0,
        w: viewWidth - sw,
        h: viewHeight - ih
    };
}

// =============================================================================
// SIDEBAR
// =============================================================================

function drawSidebar() {
    // Background
    mgraphics.set_source_rgba(colors.bgSidebar);
    mgraphics.rectangle(sidebarArea.x, sidebarArea.y, sidebarArea.w, sidebarArea.h);
    mgraphics.fill();

    // Divider line
    mgraphics.set_source_rgba(colors.divider);
    mgraphics.rectangle(sidebarArea.x, 0, 1, viewHeight);
    mgraphics.fill();

    // Draw buttons
    var buttons = layout.sidebar.buttons;
    var btnH = layout.sidebar.buttonHeight;

    for (var i = 0; i < buttons.length; i++) {
        var btn = buttons[i];
        var btnY = i * btnH;
        var isActive = (activeButton === i);
        var isHovered = (hoveredButton === i);

        // Button background
        var bgColor = isActive ? colors.bgButtonActive :
                      isHovered ? colors.bgButtonHover : colors.bgSidebar;
        mgraphics.set_source_rgba(bgColor);
        mgraphics.rectangle(sidebarArea.x + 1, btnY, sidebarArea.w - 1, btnH);
        mgraphics.fill();

        // Button icon/text
        mgraphics.select_font_face(config.fontName);
        mgraphics.set_font_size(16);

        var textColor = isActive ? colors.bgInput : colors.textSecondary;
        mgraphics.set_source_rgba(textColor);

        var metrics = mgraphics.text_measure(btn.icon);
        var textX = sidebarArea.x + (sidebarArea.w - metrics[0]) / 2;
        var textY = btnY + (btnH + 12) / 2;

        mgraphics.move_to(textX, textY);
        mgraphics.text_path(btn.icon);
        mgraphics.fill();
    }
}

// =============================================================================
// INPUT AREA
// =============================================================================

function drawInputArea() {
    // Background
    mgraphics.set_source_rgba(colors.bgInput);
    mgraphics.rectangle(inputArea.x, inputArea.y, inputArea.w, inputArea.h);
    mgraphics.fill();

    // Top divider
    mgraphics.set_source_rgba(colors.divider);
    mgraphics.rectangle(inputArea.x, inputArea.y, inputArea.w, 1);
    mgraphics.fill();

    // > prompt
    mgraphics.select_font_face(config.fontName);
    mgraphics.set_font_size(14);
    mgraphics.set_source_rgba(colors.textMuted);
    mgraphics.move_to(inputArea.x + 10, inputArea.y + inputArea.h/2 + 5);
    mgraphics.text_path(">");
    mgraphics.fill();

    // Send button
    var sendBg = hoveredSend ? colors.bgButtonHover : colors.bgInput;
    mgraphics.set_source_rgba(sendBg);
    mgraphics.rectangle(sendButtonArea.x, sendButtonArea.y, sendButtonArea.w, sendButtonArea.h);
    mgraphics.fill();

    // Send button divider
    mgraphics.set_source_rgba(colors.divider);
    mgraphics.rectangle(sendButtonArea.x, sendButtonArea.y + 8, 1, sendButtonArea.h - 16);
    mgraphics.fill();

    // Send icon
    mgraphics.set_font_size(16);
    mgraphics.set_source_rgba(hoveredSend ? colors.accentOrange : colors.textSecondary);
    var sendMetrics = mgraphics.text_measure(">");
    var sendX = sendButtonArea.x + (sendButtonArea.w - sendMetrics[0]) / 2;
    var sendY = sendButtonArea.y + (sendButtonArea.h + 12) / 2;
    mgraphics.move_to(sendX, sendY);
    mgraphics.text_path(">");
    mgraphics.fill();
}

// =============================================================================
// CHAT AREA
// =============================================================================

function drawChatArea() {
    // Background
    mgraphics.set_source_rgba(colors.bgPrimary);
    mgraphics.rectangle(chatArea.x, chatArea.y, chatArea.w, chatArea.h);
    mgraphics.fill();

    if (currentView !== "chat") {
        drawStaticContent();
        return;
    }

    if (messages.length === 0) {
        drawEmptyState();
        return;
    }

    // Rewrap messages if needed
    var needsRecalc = false;
    for (var j = 0; j < messages.length; j++) {
        if (messages[j].needsRewrap) {
            wrapMessageText(messages[j]);
            needsRecalc = true;
        }
    }
    if (needsRecalc) {
        recalculateHeights();
        scrollToBottom();
    }

    // Draw messages
    var y = chatArea.y - scrollOffset;

    for (var i = 0; i < messages.length; i++) {
        var msg = messages[i];
        var msgHeight = msg.height;

        // Skip messages entirely above viewport
        if (y + msgHeight < chatArea.y) {
            y += msgHeight + config.messageGap;
            continue;
        }

        // Stop if we're past the chat area (input area will cover any partial)
        if (y > chatArea.y + chatArea.h) {
            break;
        }

        drawMessage(msg, y, i);
        y += msgHeight + config.messageGap;
    }

    // Scrollbar
    if (totalHeight > chatArea.h) {
        drawScrollbar();
    }

    // Thinking indicator
    if (isThinking) {
        drawThinkingIndicator();
    }
}

function drawThinkingIndicator() {
    var y = chatArea.y + totalHeight - scrollOffset + config.messageGap;

    // If we'd draw below the chat area, adjust
    if (y < chatArea.y) y = chatArea.y + 10;
    if (y > chatArea.y + chatArea.h - 30) y = chatArea.y + chatArea.h - 30;

    // Background
    mgraphics.set_source_rgba(colors.aiBg);
    mgraphics.rectangle(chatArea.x, y, chatArea.w, 30);
    mgraphics.fill();

    // "AI:" label
    mgraphics.select_font_face(config.fontName);
    mgraphics.set_font_size(config.fontSize);
    mgraphics.set_source_rgba(colors.accentBlue);
    mgraphics.move_to(chatArea.x + config.padding.x, y + 20);
    mgraphics.text_path("AI:");
    mgraphics.fill();

    // "thinking..." text
    mgraphics.set_source_rgba(colors.textMuted);
    var senderMetrics = mgraphics.text_measure("AI: ");
    mgraphics.move_to(chatArea.x + config.padding.x + senderMetrics[0], y + 20);
    mgraphics.text_path("thinking...");
    mgraphics.fill();
}

function drawEmptyState() {
    mgraphics.select_font_face(config.fontName);
    mgraphics.set_font_size(config.fontSize);
    mgraphics.set_source_rgba(colors.textSecondary);

    var lines = [
        "Welcome to ChatM4L!",
        "",
        "Type a message below to start chatting.",
        "Use /help for commands."
    ];

    var startY = chatArea.y + (chatArea.h / 2) - ((lines.length * config.lineHeight) / 2);

    for (var i = 0; i < lines.length; i++) {
        var metrics = mgraphics.text_measure(lines[i]);
        var x = chatArea.x + (chatArea.w - metrics[0]) / 2;
        mgraphics.move_to(x, startY + (i * config.lineHeight));
        mgraphics.text_path(lines[i]);
        mgraphics.fill();
    }
}

function drawStaticContent() {
    var content = getStaticContent(currentView);
    var lines = content.split("\n");

    mgraphics.select_font_face(config.fontName);
    mgraphics.set_font_size(config.fontSize);
    mgraphics.set_source_rgba(colors.textPrimary);

    var y = chatArea.y + config.padding.y + config.fontSize;

    for (var i = 0; i < lines.length; i++) {
        var line = lines[i];

        // Check for header (starts with uppercase and no other text patterns)
        if (line === line.toUpperCase() && line.length > 0 && line.indexOf(":") === -1) {
            mgraphics.set_source_rgba(colors.accentOrange);
        } else if (line.indexOf("─") !== -1) {
            mgraphics.set_source_rgba(colors.textMuted);
        } else {
            mgraphics.set_source_rgba(colors.textSecondary);
        }

        mgraphics.move_to(chatArea.x + config.padding.x, y);
        mgraphics.text_path(line);
        mgraphics.fill();

        y += config.lineHeight;
    }
}

function getStaticContent(view) {
    switch (view) {
        case "settings":
            return "SETTINGS\n─────────────────────────\n\nProvider: (from status)\nModel: (from status)\n\nStatus: Ready\n\n─────────────────────────\n\nConfig location:\n~/Library/Application Support/ChatM4L/\n\nCommands:\n/reload - Reload config\n/openconfig - Show config path";
        case "skills":
            return "SKILLS\n─────────────────────────\n\nUse /<skill> to apply expertise:\n\n/drums - Drum patterns\n/mixing - Mix engineering\n/sound-design - Sound design\n\n─────────────────────────\n\nSkills are one-shot by default.\nUse /skill <name> to persist.";
        case "profile":
            return "PROFILE\n─────────────────────────\n\nYour profile helps ChatM4L\nunderstand your style.\n\nEdit: core/user.md\n\n─────────────────────────\n\nInclude:\n- Genres & influences\n- Reference artists\n- Sound preferences\n- Hardware & plugins";
        case "help":
            return "HELP\n─────────────────────────\n\nCOMMANDS\n\n/help      Show this help\n/status    Show status\n/newchat   Clear conversation\n/reload    Reload config\n/skills    List skills\n/<skill>   Apply skill\n\n─────────────────────────\n\nTIPS\n\nJust type naturally!\nAI sees your track context.\nUse /drums, /mixing, etc.";
        default:
            return "";
    }
}

function drawMessage(msg, y, index) {
    var bgColor;
    switch (msg.type) {
        case "ai":
            bgColor = index % 2 === 0 ? colors.aiBg : colors.bgSecondary;
            break;
        case "system":
            bgColor = colors.systemBg;
            break;
        case "error":
            bgColor = colors.errorBg;
            break;
        default:
            bgColor = index % 2 === 0 ? colors.userBg : colors.bgPrimary;
    }

    mgraphics.set_source_rgba(bgColor);
    mgraphics.rectangle(chatArea.x, y, chatArea.w, msg.height);
    mgraphics.fill();

    mgraphics.select_font_face(config.fontName);
    mgraphics.set_font_size(config.fontSize);

    var senderColor = msg.type === "ai" ? colors.accentBlue : colors.accentOrange;
    mgraphics.set_source_rgba(senderColor);
    mgraphics.move_to(chatArea.x + config.padding.x, y + config.messagePadding + config.fontSize);
    mgraphics.text_path(msg.sender + ":");
    mgraphics.fill();

    var senderMetrics = mgraphics.text_measure(msg.sender + ": ");
    var textX = chatArea.x + config.padding.x + senderMetrics[0];

    mgraphics.set_source_rgba(colors.textPrimary);

    for (var i = 0; i < msg.lines.length; i++) {
        var lineY = y + config.messagePadding + config.fontSize + (i * config.lineHeight);
        var lineX = i === 0 ? textX : chatArea.x + config.padding.x + 20;

        mgraphics.move_to(lineX, lineY);
        mgraphics.text_path(msg.lines[i]);
        mgraphics.fill();
    }
}

function drawScrollbar() {
    var maxScroll = totalHeight - chatArea.h;
    if (maxScroll <= 0) return;

    var scrollbarHeight = 40;
    var scrollbarWidth = 4;
    var scrollRange = chatArea.h - scrollbarHeight - 10;
    var scrollY = chatArea.y + 5 + (scrollOffset / maxScroll) * scrollRange;

    mgraphics.set_source_rgba([0.3, 0.3, 0.3, 0.5]);
    mgraphics.rectangle(chatArea.x + chatArea.w - scrollbarWidth - 5, chatArea.y + 5, scrollbarWidth, chatArea.h - 10);
    mgraphics.fill();

    mgraphics.set_source_rgba(colors.accentOrange);
    mgraphics.rectangle(chatArea.x + chatArea.w - scrollbarWidth - 5, scrollY, scrollbarWidth, scrollbarHeight);
    mgraphics.fill();
}

// =============================================================================
// MESSAGE MANAGEMENT
// =============================================================================

function message() {
    var args = arrayfromargs(arguments);
    if (args.length < 2) return;
    addMessageInternal(args[0], args.slice(1).join(" "));
}

function anything() {
    var sender = messagename;
    var args = arrayfromargs(arguments);

    post("anything() sender: [" + sender + "] args: " + args + "\n");

    // Handle thinking message
    if (sender.toString().toLowerCase().indexOf("thinking") >= 0) {
        isThinking = (args[0] == 1);
        post("Setting isThinking to: " + isThinking + "\n");
        mgraphics.redraw();
        return;
    }

    // Skip other control messages
    if (sender === "setView" || sender === "clear" || sender === "bang") {
        return;
    }

    var text = args.join(" ");
    if (text.length > 0) {
        addMessageInternal(sender, text);
    }
}

function addMessageInternal(sender, text) {
    // Turn off thinking indicator when message arrives
    if (sender.toLowerCase() === "ai" || sender.toLowerCase() === "assistant") {
        isThinking = false;
    }

    var type = "user";
    var senderLower = sender.toLowerCase();
    if (senderLower === "ai" || senderLower === "assistant" || senderLower === "chatm4l") {
        type = "ai";
    } else if (senderLower === "system" || senderLower === "error") {
        type = "system";
    }
    if (senderLower === "error") {
        type = "error";
    }

    // Estimate lines for initial height (will be recalculated in paint)
    var estimatedCharsPerLine = 50;
    var estimatedLines = Math.ceil(text.length / estimatedCharsPerLine) || 1;
    var estimatedHeight = (estimatedLines * config.lineHeight) + (config.messagePadding * 2);

    var msg = {
        sender: sender,
        text: text,
        type: type,
        lines: [text],  // Temporary - will be wrapped in paint()
        height: estimatedHeight,
        needsRewrap: true  // Always rewrap in paint() where mgraphics is valid
    };

    // Don't call wrapMessageText() here - mgraphics not available outside paint()
    // The paint() cycle will handle wrapping via needsRewrap flag

    messages.push(msg);

    // Switch to chat view if not already
    if (currentView !== "chat") {
        setView("chat");
    }

    recalculateHeights();
    scrollToBottom();
    mgraphics.redraw();
}

function wrapMessageText(msg) {
    // NOTE: This function should ONLY be called from inside paint()
    // where mgraphics context is valid. Called from drawChatArea().

    var maxWidth = chatArea.w - (config.padding.x * 2) - 60;
    if (maxWidth < 100) maxWidth = 100;

    var words = msg.text.split(" ");
    var lines = [];
    var currentLine = "";

    // Try to use mgraphics for accurate text measurement
    // This works because we're called from inside paint()
    var canMeasure = false;
    try {
        mgraphics.select_font_face(config.fontName);
        mgraphics.set_font_size(config.fontSize);
        var testMetrics = mgraphics.text_measure("test");
        canMeasure = (testMetrics && testMetrics[0] > 0);
    } catch (e) {
        canMeasure = false;
    }

    if (canMeasure) {
        for (var i = 0; i < words.length; i++) {
            var testLine = currentLine + (currentLine ? " " : "") + words[i];
            var metrics = mgraphics.text_measure(testLine);

            if (metrics[0] > maxWidth && currentLine) {
                lines.push(currentLine);
                currentLine = words[i];
            } else {
                currentLine = testLine;
            }
        }
        if (currentLine) {
            lines.push(currentLine);
        }
    } else {
        var charsPerLine = Math.floor(maxWidth / 7);
        if (charsPerLine < 20) charsPerLine = 40;

        var text = msg.text;
        while (text.length > 0) {
            if (text.length <= charsPerLine) {
                lines.push(text);
                break;
            }
            var breakPoint = text.lastIndexOf(" ", charsPerLine);
            if (breakPoint <= 0) breakPoint = charsPerLine;
            lines.push(text.substring(0, breakPoint));
            text = text.substring(breakPoint + 1);
        }
    }

    msg.lines = lines.length > 0 ? lines : [""];
    msg.height = (msg.lines.length * config.lineHeight) + (config.messagePadding * 2);
    msg.needsRewrap = false;
}

function recalculateHeights() {
    // Just sum existing heights - don't call wrapMessageText here
    // Text wrapping happens in paint() via drawChatArea()'s needsRewrap check
    totalHeight = 0;
    for (var i = 0; i < messages.length; i++) {
        totalHeight += messages[i].height + config.messageGap;
    }
}

// =============================================================================
// SCROLLING
// =============================================================================

function scroll(amount) {
    scrollOffset += amount;
    clampScroll();
    mgraphics.redraw();
}

function scrolltobottom() {
    scrollToBottom();
    mgraphics.redraw();
}

function scrollToBottom() {
    var maxScroll = Math.max(0, totalHeight - chatArea.h);
    scrollOffset = maxScroll;
}

function clampScroll() {
    var maxScroll = Math.max(0, totalHeight - chatArea.h);
    if (scrollOffset < 0) scrollOffset = 0;
    if (scrollOffset > maxScroll) scrollOffset = maxScroll;
}

// =============================================================================
// VIEW MANAGEMENT
// =============================================================================

function setView(viewName) {
    var validViews = ["chat", "settings", "skills", "profile", "help"];
    var viewIndex = validViews.indexOf(viewName);
    if (viewIndex === -1) return;

    currentView = viewName;
    activeButton = viewIndex - 1;  // -1 for chat, 0-3 for others

    mgraphics.redraw();

    // Notify bridge
    outlet(0, "view", viewName);
}

function clear() {
    messages = [];
    scrollOffset = 0;
    totalHeight = 0;
    isThinking = false;
    mgraphics.redraw();
}

/**
 * Show/hide thinking indicator
 * Called from bridge.js: thinking 1 (show) or thinking 0 (hide)
 */
function thinking(show) {
    isThinking = (show == 1);
    mgraphics.redraw();
}

// =============================================================================
// MOUSE INTERACTION
// =============================================================================

function onclick(x, y, button, mod1, shift, caps, opt, mod2) {
    // Check sidebar buttons
    if (x >= sidebarArea.x) {
        var btnIndex = Math.floor(y / layout.sidebar.buttonHeight);
        if (btnIndex >= 0 && btnIndex < layout.sidebar.buttons.length) {
            var views = ["settings", "skills", "profile", "help"];
            if (activeButton === btnIndex) {
                // Clicking active button returns to chat
                setView("chat");
            } else {
                setView(views[btnIndex]);
            }
            return;
        }
    }

    // Check send button
    if (x >= sendButtonArea.x && x < sendButtonArea.x + sendButtonArea.w &&
        y >= sendButtonArea.y && y < sendButtonArea.y + sendButtonArea.h) {
        outlet(0, "send");
        return;
    }

    // Click in chat area - could be used for scrolling
}

function ondrag(x, y, button, mod1, shift, caps, opt, mod2) {
    // Drag scrolling in chat area
    if (x < chatArea.x + chatArea.w && y < chatArea.y + chatArea.h) {
        // Handled by onidle tracking
    }
}

function onidle(x, y, button, mod1, shift, caps, opt, mod2) {
    var needsRedraw = false;

    // Check sidebar hover
    var newHovered = -1;
    if (x >= sidebarArea.x) {
        var btnIndex = Math.floor(y / layout.sidebar.buttonHeight);
        if (btnIndex >= 0 && btnIndex < layout.sidebar.buttons.length) {
            newHovered = btnIndex;
        }
    }
    if (newHovered !== hoveredButton) {
        hoveredButton = newHovered;
        needsRedraw = true;
    }

    // Check send button hover
    var newSendHover = (x >= sendButtonArea.x && x < sendButtonArea.x + sendButtonArea.w &&
                        y >= sendButtonArea.y && y < sendButtonArea.y + sendButtonArea.h);
    if (newSendHover !== hoveredSend) {
        hoveredSend = newSendHover;
        needsRedraw = true;
    }

    if (needsRedraw) {
        mgraphics.redraw();
    }
}

function onidleout() {
    if (hoveredButton !== -1 || hoveredSend) {
        hoveredButton = -1;
        hoveredSend = false;
        mgraphics.redraw();
    }
}

function onwheel(x, y, wheel_inc_x, wheel_inc_y) {
    if (currentView === "chat" && x < chatArea.x + chatArea.w) {
        scroll(-wheel_inc_y * config.scrollSpeed);
        return 1;
    }
    return 0;
}

function ondblclick(x, y, button, mod1, shift, caps, opt, mod2) {
    if (x < chatArea.x + chatArea.w && y < chatArea.y + chatArea.h) {
        scrolltobottom();
    }
}

// =============================================================================
// RESIZE
// =============================================================================

function onresize(w, h) {
    viewWidth = w;
    viewHeight = h;
    calculateAreas();
    recalculateHeights();
    clampScroll();
    mgraphics.redraw();
}

// =============================================================================
// UTILITIES
// =============================================================================

function bang() {
    mgraphics.redraw();
}

/**
 * Get the coordinates where the textedit should be placed
 * Returns: x y width height
 */
function getInputRect() {
    calculateAreas();
    outlet(0, "inputrect", inputTextArea.x, inputTextArea.y, inputTextArea.w, inputTextArea.h);
}

function dump() {
    post("--- ChatM4L UI State ---\n");
    post("View: " + currentView + "\n");
    post("Messages: " + messages.length + "\n");
    post("Size: " + viewWidth + " x " + viewHeight + "\n");
    post("Chat area: " + chatArea.w + " x " + chatArea.h + "\n");
    post("Input text area: " + inputTextArea.x + ", " + inputTextArea.y + ", " + inputTextArea.w + ", " + inputTextArea.h + "\n");
    post("------------------------\n");
}
