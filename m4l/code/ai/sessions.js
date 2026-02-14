/**
 * ChatM4L Sessions - Persistent conversation storage
 *
 * Sessions are stored per-track and auto-rotate based on:
 * - Different track = different session
 * - Time gap > 4 hours = new session
 * - Manual "new chat" command
 */

const fs = require("fs");
const path = require("path");
const { CONFIG_DIR } = require("./config");

const SESSIONS_DIR = path.join(CONFIG_DIR, "sessions");
const ARCHIVE_DIR = path.join(SESSIONS_DIR, "archive");
const GAP_THRESHOLD_MS = 4 * 60 * 60 * 1000; // 4 hours
const MAX_MESSAGES = 20; // Keep last 20 messages (10 exchanges)

/**
 * Ensure session directories exist
 */
function ensureDirectories() {
    if (!fs.existsSync(SESSIONS_DIR)) {
        fs.mkdirSync(SESSIONS_DIR, { recursive: true });
    }
    if (!fs.existsSync(ARCHIVE_DIR)) {
        fs.mkdirSync(ARCHIVE_DIR, { recursive: true });
    }
}

/**
 * Sanitize track name for use in filename
 */
function sanitizeTrackName(trackName) {
    return (trackName || "unknown").replace(/[^a-zA-Z0-9-_]/g, "_");
}

/**
 * Get path to current session file for a track
 */
function getSessionPath(trackName) {
    const safeName = sanitizeTrackName(trackName);
    return path.join(SESSIONS_DIR, `${safeName}_current.json`);
}

/**
 * Generate a short unique ID
 */
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substring(2, 6);
}

/**
 * Create a new empty session
 */
function createSession(trackName) {
    return {
        id: generateId(),
        trackName: trackName || "unknown",
        created: new Date().toISOString(),
        lastMessage: new Date().toISOString(),
        messages: []
    };
}

/**
 * Load session from disk
 */
function loadSession(trackName) {
    ensureDirectories();
    const sessionPath = getSessionPath(trackName);

    try {
        if (fs.existsSync(sessionPath)) {
            const data = fs.readFileSync(sessionPath, "utf8");
            return JSON.parse(data);
        }
    } catch (e) {
        console.error("Error loading session:", e.message);
    }
    return null;
}

/**
 * Save session to disk
 */
function saveSession(session) {
    ensureDirectories();
    const sessionPath = getSessionPath(session.trackName);

    try {
        fs.writeFileSync(sessionPath, JSON.stringify(session, null, 2));
        return true;
    } catch (e) {
        console.error("Error saving session:", e.message);
        return false;
    }
}

/**
 * Archive a session (move to archive folder)
 */
function archiveSession(session) {
    if (!session || !session.messages || session.messages.length === 0) {
        return false; // Don't archive empty sessions
    }

    ensureDirectories();

    const date = new Date(session.created).toISOString().split("T")[0];
    const safeName = sanitizeTrackName(session.trackName);
    const archivePath = path.join(ARCHIVE_DIR, `${safeName}_${date}_${session.id}.json`);

    try {
        fs.writeFileSync(archivePath, JSON.stringify(session, null, 2));

        // Remove current session file
        const currentPath = getSessionPath(session.trackName);
        if (fs.existsSync(currentPath)) {
            fs.unlinkSync(currentPath);
        }
        return true;
    } catch (e) {
        console.error("Error archiving session:", e.message);
        return false;
    }
}

/**
 * Check if session should be rotated due to time gap
 */
function isSessionExpired(session) {
    if (!session || !session.lastMessage) return true;

    const lastMessageTime = new Date(session.lastMessage).getTime();
    const now = Date.now();

    return (now - lastMessageTime) > GAP_THRESHOLD_MS;
}

/**
 * Get or create session for a track
 * Handles rotation logic automatically
 */
function getOrCreateSession(trackName) {
    let session = loadSession(trackName);

    if (session) {
        // Check if we should rotate due to time gap
        if (isSessionExpired(session)) {
            archiveSession(session);
            session = createSession(trackName);
            saveSession(session);
        }
    } else {
        session = createSession(trackName);
        saveSession(session);
    }

    return session;
}

/**
 * Add a message to the session and save
 */
function addMessage(session, role, content) {
    session.messages.push({ role, content });
    session.lastMessage = new Date().toISOString();

    // Trim to max history
    if (session.messages.length > MAX_MESSAGES) {
        session.messages = session.messages.slice(-MAX_MESSAGES);
    }

    saveSession(session);
    return session;
}

/**
 * Get messages from session (for sending to Claude)
 */
function getMessages(session) {
    return session.messages.map(msg => ({ role: msg.role, content: msg.content }));
}

/**
 * Clear current session and start fresh
 */
function clearSession(trackName) {
    const session = loadSession(trackName);
    if (session) {
        archiveSession(session);
    }
    const newSession = createSession(trackName);
    saveSession(newSession);
    return newSession;
}

/**
 * Get message count for a session
 */
function getMessageCount(session) {
    return session ? session.messages.length : 0;
}

module.exports = {
    getOrCreateSession,
    addMessage,
    getMessages,
    saveSession,
    clearSession,
    getMessageCount,
    archiveSession,
    isSessionExpired,
    GAP_THRESHOLD_MS,
    MAX_MESSAGES,
    SESSIONS_DIR,
    ARCHIVE_DIR
};
