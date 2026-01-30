// Cascade AI Client
const API_BASE_URL = 'http://localhost:8001'; // Your FastAPI server

async function getCascadeResponse(messages) {
    try {
        // Get the last user message
        const lastUserMessage = messages
            .slice()
            .reverse()
            .find(msg => msg.role === 'user');
        
        if (!lastUserMessage) {
            return "I didn't receive your message. Please try again.";
        }

        // Prepare history in the format expected by the backend
        const history = messages
            .filter(msg => msg.role !== 'system')
            .map(msg => ({
                role: msg.role,
                message: msg.content
            }));

        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: lastUserMessage.content,
                history: history
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();
        return data.response || data.text || "I'm sorry, I couldn't process your request.";
    } catch (error) {
        console.error('Error:', error);
        return error.message || "I'm having trouble connecting to the server. Please try again later.";
    }
}

// For backward compatibility
async function getCohereResponse(messages) {
    return getCascadeResponse(messages);
}
