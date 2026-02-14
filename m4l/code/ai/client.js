/**
 * ChatM4L Client - Anthropic client management
 */

let anthropicClient = null;

function initializeClient(key) {
    try {
        const Anthropic = require("@anthropic-ai/sdk");
        anthropicClient = new Anthropic({ apiKey: key });
        return true;
    } catch (e) {
        console.error("Error initializing Anthropic client:", e.message);
        return false;
    }
}

function getClient() {
    return anthropicClient;
}

function clearClient() {
    anthropicClient = null;
}

function isReady() {
    return !!anthropicClient;
}

module.exports = {
    initializeClient,
    getClient,
    clearClient,
    isReady
};
