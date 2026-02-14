/**
 * ChatM4L Client - Anthropic client management
 */

let anthropicClient = null;
let apiKey = "";

function initializeClient(key) {
    try {
        const Anthropic = require("@anthropic-ai/sdk");
        anthropicClient = new Anthropic({ apiKey: key });
        apiKey = key;
        return true;
    } catch (e) {
        console.error("Error initializing Anthropic client:", e.message);
        return false;
    }
}

function getClient() {
    return anthropicClient;
}

function getApiKey() {
    return apiKey;
}

function clearClient() {
    anthropicClient = null;
    apiKey = "";
}

function isReady() {
    return !!anthropicClient;
}

module.exports = {
    initializeClient,
    getClient,
    getApiKey,
    clearClient,
    isReady
};
