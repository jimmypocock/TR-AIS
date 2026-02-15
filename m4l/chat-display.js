/**
 * ChatM4L Chat Display - jsui component for Max for Live
 *
 * A scrollable chat display with alternating row colors,
 * text wrapping, and Ableton-style theming.
 *
 * Usage in Max:
 *   [jsui @filename chat-display.js @size 400 300]
 *
 * Messages from bridge.js:
 *   message <sender> <text>   - Add a chat message
 *   clear                     - Clear all messages
 *   scroll <amount>           - Scroll by amount (positive = down)
 *   scrolltobottom            - Scroll to newest message
 *
 * Outlets:
 *   0: Status messages (e.g., "scrolled", "cleared")
 */

// =============================================================================
// JSUI SETUP
// =============================================================================

autowatch = 1;  // Hot reload on file save
mgraphics.init();
mgraphics.relative_coords = 0;
mgraphics.autofill = 0;

inlets = 1;
outlets = 1;

// =============================================================================
// CONFIGURATION
// =============================================================================

var config = {
    // Typography
    fontName: "Ableton Sans Medium",
    fontFallback: "Arial",
    fontSize: 12,
    lineHeight: 18,
    padding: {
        x: 10,
        y: 6
    },

    // Message spacing
    messagePadding: 8,  // Vertical padding inside each message bubble
    messageGap: 2,      // Gap between messages

    // Scrolling
    scrollSpeed: 40,    // Pixels per scroll tick

    // Colors (Ableton-style) - RGBA 0-1 range
    colors: {
        // Backgrounds
        bgPrimary:   [0.239, 0.239, 0.239, 1],    // #3D3D3D
        bgSecondary: [0.196, 0.196, 0.196, 1],    // #323232
        bgInput:     [0.102, 0.102, 0.102, 1],    // #1A1A1A

        // Text
        textPrimary:   [1, 1, 1, 1],              // #FFFFFF
        textSecondary: [0.702, 0.702, 0.702, 1],  // #B3B3B3
        textMuted:     [0.502, 0.502, 0.502, 1],  // #808080

        // Accents
        accentOrange: [0.961, 0.651, 0.137, 1],   // #F5A623
        accentBlue:   [0.314, 0.784, 1, 1],       // #50C8FF

        // Message-specific
        userBg:    [0.165, 0.165, 0.165, 1],      // Darker for user
        aiBg:      [0.220, 0.220, 0.220, 1],      // Slightly lighter for AI
        systemBg:  [0.180, 0.180, 0.180, 1],      // System messages
        errorBg:   [0.3, 0.15, 0.15, 1]           // Error tint
    }
};

// =============================================================================
// STATE
// =============================================================================

var messages = [];          // Array of {sender, text, type, lines[]}
var scrollOffset = 0;       // Current scroll position (pixels from top)
var totalHeight = 0;        // Total content height
var viewHeight = 0;         // Visible area height
var viewWidth = 0;          // Visible area width
var isDragging = false;     // Mouse drag state
var lastMouseY = 0;         // For drag scrolling
var hasGraphicsContext = false;  // Set true after first successful paint

// =============================================================================
// MESSAGE MANAGEMENT
// =============================================================================

/**
 * Add a message to the chat
 * Called via: message <sender> <text...>
 */
function message() {
    var args = arrayfromargs(arguments);
    if (args.length < 2) return;

    var sender = args[0];
    var text = args.slice(1).join(" ");

    addMessageInternal(sender, text);
}

/**
 * Catch-all for messages where the function name is the sender
 * (v8 outlet sends "You hello" which calls You("hello") instead of message("You", "hello"))
 */
function anything() {
    // messagename is a special jsui variable containing the called function name
    var sender = messagename;
    var args = arrayfromargs(arguments);
    var text = args.join(" ");

    if (text.length > 0) {
        addMessageInternal(sender, text);
    }
}

/**
 * Internal: add a message to the display
 */
function addMessageInternal(sender, text) {
    // Determine message type
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

    // Create message object
    var msg = {
        sender: sender,
        text: text,
        type: type,
        lines: [],      // Will be populated by wrapText
        height: 0       // Will be calculated
    };

    // Wrap text to fit width
    wrapMessageText(msg);

    messages.push(msg);

    // Auto-scroll to bottom
    recalculateHeights();
    scrollToBottom();

    mgraphics.redraw();
}

/**
 * Clear all messages
 */
function clear() {
    messages = [];
    scrollOffset = 0;
    totalHeight = 0;
    mgraphics.redraw();
    outlet(0, "cleared");
}

/**
 * Wrap message text to fit display width
 */
function wrapMessageText(msg) {
    var maxWidth = viewWidth - (config.padding.x * 2) - 60; // Leave room for sender
    if (maxWidth < 100) maxWidth = 100;

    var words = msg.text.split(" ");
    var lines = [];
    var currentLine = "";

    // Check if we have a graphics context for text measurement
    // Only attempt if we've had at least one successful paint
    var canMeasure = false;
    if (hasGraphicsContext) {
        try {
            mgraphics.select_font_face(config.fontName);
            mgraphics.set_font_size(config.fontSize);
            var testMetrics = mgraphics.text_measure("test");
            canMeasure = (testMetrics && testMetrics[0] > 0);
        } catch (e) {
            canMeasure = false;
        }
    }

    if (canMeasure) {
        // Proper text wrapping with measurement
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
        // Fallback: estimate ~7 pixels per character
        var charsPerLine = Math.floor(maxWidth / 7);
        if (charsPerLine < 20) charsPerLine = 40;

        var text = msg.text;
        while (text.length > 0) {
            if (text.length <= charsPerLine) {
                lines.push(text);
                break;
            }
            // Find last space within limit
            var breakPoint = text.lastIndexOf(" ", charsPerLine);
            if (breakPoint <= 0) breakPoint = charsPerLine;
            lines.push(text.substring(0, breakPoint));
            text = text.substring(breakPoint + 1);
        }
    }

    msg.lines = lines.length > 0 ? lines : [""];
    msg.height = (msg.lines.length * config.lineHeight) + (config.messagePadding * 2);
    msg.needsRewrap = !canMeasure;  // Flag to rewrap on next paint
}

/**
 * Recalculate all message heights and total content height
 */
function recalculateHeights() {
    totalHeight = 0;
    for (var i = 0; i < messages.length; i++) {
        wrapMessageText(messages[i]);
        totalHeight += messages[i].height + config.messageGap;
    }
}

// =============================================================================
// SCROLLING
// =============================================================================

/**
 * Scroll by a relative amount
 */
function scroll(amount) {
    scrollOffset += amount;
    clampScroll();
    mgraphics.redraw();
}

/**
 * Scroll to the bottom (newest messages)
 */
function scrolltobottom() {
    scrollToBottom();
    mgraphics.redraw();
}

function scrollToBottom() {
    var maxScroll = Math.max(0, totalHeight - viewHeight);
    scrollOffset = maxScroll;
}

/**
 * Ensure scroll position is within bounds
 */
function clampScroll() {
    var maxScroll = Math.max(0, totalHeight - viewHeight);
    if (scrollOffset < 0) scrollOffset = 0;
    if (scrollOffset > maxScroll) scrollOffset = maxScroll;
}

// =============================================================================
// RENDERING
// =============================================================================

function paint() {
    viewWidth = mgraphics.size[0];
    viewHeight = mgraphics.size[1];
    hasGraphicsContext = true;  // We now have a valid context

    // Background
    mgraphics.set_source_rgba(config.colors.bgPrimary);
    mgraphics.rectangle(0, 0, viewWidth, viewHeight);
    mgraphics.fill();

    if (messages.length === 0) {
        drawEmptyState();
        return;
    }

    // Rewrap any messages that were added before graphics context was ready
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
    var y = -scrollOffset;

    for (var i = 0; i < messages.length; i++) {
        var msg = messages[i];
        var msgHeight = msg.height;

        // Skip if completely above viewport
        if (y + msgHeight < 0) {
            y += msgHeight + config.messageGap;
            continue;
        }

        // Stop if below viewport
        if (y > viewHeight) {
            break;
        }

        drawMessage(msg, y, i);
        y += msgHeight + config.messageGap;
    }

    // Draw scroll indicators if needed
    if (totalHeight > viewHeight) {
        drawScrollIndicators();
    }
}

function drawEmptyState() {
    mgraphics.select_font_face(config.fontName);
    mgraphics.set_font_size(config.fontSize);
    mgraphics.set_source_rgba(config.colors.textSecondary);

    var lines = [
        "Welcome to ChatM4L!",
        "",
        "Type a message below to start chatting.",
        "Use /help for commands."
    ];

    var startY = (viewHeight / 2) - ((lines.length * config.lineHeight) / 2);

    for (var i = 0; i < lines.length; i++) {
        var metrics = mgraphics.text_measure(lines[i]);
        var x = (viewWidth - metrics[0]) / 2;
        mgraphics.move_to(x, startY + (i * config.lineHeight));
        mgraphics.text_path(lines[i]);
        mgraphics.fill();
    }
}

function drawMessage(msg, y, index) {
    // Determine background color based on message type and alternating
    var bgColor;
    switch (msg.type) {
        case "ai":
            bgColor = index % 2 === 0 ? config.colors.aiBg : config.colors.bgSecondary;
            break;
        case "system":
            bgColor = config.colors.systemBg;
            break;
        case "error":
            bgColor = config.colors.errorBg;
            break;
        default: // user
            bgColor = index % 2 === 0 ? config.colors.userBg : config.colors.bgPrimary;
    }

    // Message background
    mgraphics.set_source_rgba(bgColor);
    mgraphics.rectangle(0, y, viewWidth, msg.height);
    mgraphics.fill();

    // Sender label
    mgraphics.select_font_face(config.fontName);
    mgraphics.set_font_size(config.fontSize);

    var senderColor = msg.type === "ai" ? config.colors.accentBlue :
                      msg.type === "error" ? config.colors.accentOrange :
                      config.colors.accentOrange;

    mgraphics.set_source_rgba(senderColor);
    mgraphics.move_to(config.padding.x, y + config.messagePadding + config.fontSize);
    mgraphics.text_path(msg.sender + ":");
    mgraphics.fill();

    // Measure sender width for text offset
    var senderMetrics = mgraphics.text_measure(msg.sender + ": ");
    var textX = config.padding.x + senderMetrics[0];

    // Message text
    mgraphics.set_source_rgba(config.colors.textPrimary);

    for (var i = 0; i < msg.lines.length; i++) {
        var lineY = y + config.messagePadding + config.fontSize + (i * config.lineHeight);
        var lineX = i === 0 ? textX : config.padding.x + 20; // Indent wrapped lines slightly

        mgraphics.move_to(lineX, lineY);
        mgraphics.text_path(msg.lines[i]);
        mgraphics.fill();
    }
}

function drawScrollIndicators() {
    var maxScroll = totalHeight - viewHeight;
    if (maxScroll <= 0) return;

    var scrollbarHeight = 40;
    var scrollbarWidth = 4;
    var scrollRange = viewHeight - scrollbarHeight - 10;
    var scrollY = 5 + (scrollOffset / maxScroll) * scrollRange;

    // Scrollbar track
    mgraphics.set_source_rgba([0.3, 0.3, 0.3, 0.5]);
    mgraphics.rectangle(viewWidth - scrollbarWidth - 5, 5, scrollbarWidth, viewHeight - 10);
    mgraphics.fill();

    // Scrollbar thumb
    mgraphics.set_source_rgba(config.colors.accentOrange);
    mgraphics.rectangle(viewWidth - scrollbarWidth - 5, scrollY, scrollbarWidth, scrollbarHeight);
    mgraphics.fill();
}

// =============================================================================
// MOUSE INTERACTION
// =============================================================================

function onclick(x, y, button, mod1, shift, caps, opt, mod2) {
    isDragging = true;
    lastMouseY = y;
}

function ondrag(x, y, button, mod1, shift, caps, opt, mod2) {
    if (isDragging) {
        var delta = lastMouseY - y;
        scroll(delta);
        lastMouseY = y;
    }
}

function onidleout(x, y, button, mod1, shift, caps, opt, mod2) {
    isDragging = false;
}

function ondblclick(x, y, button, mod1, shift, caps, opt, mod2) {
    // Double-click scrolls to bottom
    scrolltobottom();
}

// Mouse wheel scrolling
function onwheel(x, y, wheel_inc_x, wheel_inc_y) {
    scroll(-wheel_inc_y * config.scrollSpeed);
    return 1; // Consume the event
}

// =============================================================================
// RESIZE HANDLING
// =============================================================================

function onresize(w, h) {
    viewWidth = w;
    viewHeight = h;

    // Rewrap all messages for new width
    recalculateHeights();
    clampScroll();

    mgraphics.redraw();
}

// =============================================================================
// UTILITY
// =============================================================================

function bang() {
    mgraphics.redraw();
}

// Debug: dump state
function dump() {
    post("--- Chat Display State ---\n");
    post("Messages: " + messages.length + "\n");
    post("Total height: " + totalHeight + "\n");
    post("View size: " + viewWidth + " x " + viewHeight + "\n");
    post("Scroll offset: " + scrollOffset + "\n");
    post("--------------------------\n");
}
