/**
 * ChatM4L Client - Multi-provider AI client management
 *
 * Supports:
 * - Anthropic (Claude)
 * - OpenAI (GPT)
 * - OpenAI-compatible APIs (Ollama, LM Studio, etc.)
 */

let activeClient = null;
let activeProvider = null;
let activeModel = null;

/**
 * Initialize client based on provider config
 *
 * @param {string} providerName - "anthropic", "openai", or custom
 * @param {object} providerConfig - { apiKey, baseUrl, models }
 * @param {string} modelKey - Key from models object (e.g., "default", "fast")
 */
function initializeClient(providerName, providerConfig, modelKey = "default") {
    try {
        const model = providerConfig.models[modelKey] || providerConfig.models.default;

        if (providerName === "anthropic") {
            const Anthropic = require("@anthropic-ai/sdk");
            const options = { apiKey: providerConfig.apiKey };

            if (providerConfig.baseUrl) {
                options.baseURL = providerConfig.baseUrl;
            }

            activeClient = new Anthropic(options);
            activeProvider = "anthropic";
            activeModel = model;

            console.log(`Initialized Anthropic client with model: ${model}`);
            return true;

        } else if (providerName === "openai" || providerConfig.baseUrl) {
            // OpenAI or any OpenAI-compatible API (Ollama, LM Studio, etc.)
            const OpenAI = require("openai");
            const options = {
                apiKey: providerConfig.apiKey || "dummy-key-for-local"
            };

            if (providerConfig.baseUrl) {
                options.baseURL = providerConfig.baseUrl;
            }

            activeClient = new OpenAI(options);
            activeProvider = providerName;
            activeModel = model;

            console.log(`Initialized ${providerName} client with model: ${model}`);
            return true;

        } else {
            console.error(`Unknown provider: ${providerName}`);
            return false;
        }

    } catch (e) {
        console.error(`Error initializing ${providerName} client:`, e.message);
        return false;
    }
}

/**
 * Send a message to the AI and get a response
 *
 * @param {string} systemPrompt - System instructions
 * @param {array} messages - Conversation history [{ role, content }]
 * @param {object} options - { maxTokens }
 * @returns {string} - The AI's response text
 */
async function sendMessage(systemPrompt, messages, options = {}) {
    const maxTokens = options.maxTokens || 1024;

    if (!activeClient) {
        throw new Error("Client not initialized");
    }

    if (activeProvider === "anthropic") {
        const response = await activeClient.messages.create({
            model: activeModel,
            max_tokens: maxTokens,
            system: systemPrompt,
            messages: messages
        });

        return response.content[0].text;

    } else {
        // OpenAI-compatible API
        const openaiMessages = [
            { role: "system", content: systemPrompt },
            ...messages
        ];

        const response = await activeClient.chat.completions.create({
            model: activeModel,
            max_tokens: maxTokens,
            messages: openaiMessages
        });

        return response.choices[0].message.content;
    }
}

/**
 * Get the active client instance (for advanced use)
 */
function getClient() {
    return activeClient;
}

/**
 * Get current provider name
 */
function getProvider() {
    return activeProvider;
}

/**
 * Get current model name
 */
function getModel() {
    return activeModel;
}

/**
 * Clear the active client
 */
function clearClient() {
    activeClient = null;
    activeProvider = null;
    activeModel = null;
}

/**
 * Check if client is ready
 */
function isReady() {
    return !!activeClient;
}

module.exports = {
    initializeClient,
    sendMessage,
    getClient,
    getProvider,
    getModel,
    clearClient,
    isReady
};
