/**
 * ChatM4L Conversation - Conversation history management
 */

const MAX_HISTORY = 20; // Keep last 20 messages (10 exchanges)

let conversationHistory = [];

/**
 * Add a message to the conversation history
 * @param {string} role - "user" or "assistant"
 * @param {string} content - The message content
 */
function addMessage(role, content) {
    conversationHistory.push({ role, content });

    // Trim to max history
    if (conversationHistory.length > MAX_HISTORY) {
        conversationHistory = conversationHistory.slice(-MAX_HISTORY);
    }
}

/**
 * Get all messages in the conversation
 * @returns {Array} Array of message objects
 */
function getMessages() {
    return [...conversationHistory];
}

/**
 * Clear all conversation history
 */
function clear() {
    conversationHistory = [];
}

/**
 * Get the number of messages in history
 * @returns {number}
 */
function getLength() {
    return conversationHistory.length;
}

module.exports = {
    addMessage,
    getMessages,
    clear,
    getLength,
    MAX_HISTORY
};
