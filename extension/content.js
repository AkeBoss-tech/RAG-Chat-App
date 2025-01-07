// Create the chat icon
const chatIcon = document.createElement("div");
chatIcon.id = "chat-icon";
chatIcon.style.cssText = `
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: #0078d7;
  color: white;
  width: 50px;
  height: 50px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  cursor: pointer;
  z-index: 10000;
`;
chatIcon.innerText = "💬";
document.body.appendChild(chatIcon);

// Persistent session ID
let sessionId = localStorage.getItem("session_id") || null;

// Create the chat interface
const chatBox = document.createElement("div");
chatBox.id = "chat-box";
chatBox.style.cssText = `
  display: none;
  position: fixed;
  bottom: 80px;
  right: 20px;
  width: 300px;
  height: 400px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  z-index: 10000;
`;
chatBox.innerHTML = `
  <div style="background: #0078d7; color: white; padding: 10px; border-radius: 10px 10px 0 0; text-align: center;">
    Chat with XYZ
  </div>
  <div id="chat-content" style="padding: 10px; height: 300px; overflow-y: auto;">
    <p>Hi! How can I help you today?</p>
  </div>
  <input id="chat-input" type="text" placeholder="Type a message..." style="width: 100%; padding: 10px; border: none; border-top: 1px solid #ccc;" />
`;

document.body.appendChild(chatBox);

function appendMessage(role, content) {
  const messageElem = document.createElement("p");
  messageElem.textContent = `${role}: ${content}`;
  const chatContent = document.getElementById("chat-content");
  chatContent.appendChild(messageElem);
  chatContent.scrollTop = chatContent.scrollHeight;
}

// Toggle the chat interface
chatIcon.addEventListener("click", () => {
  chatBox.style.display = chatBox.style.display === "none" ? "block" : "none";
});

// Add input handling
const chatInput = document.getElementById("chat-input");
chatInput.addEventListener("keypress", async (e) => {
  if (e.key === "Enter") {
    const userMessage = chatInput.value.trim();
    if (userMessage) {
      appendMessage("You", userMessage);

      chatInput.value = "";

      try {
        const response = await fetch("http://127.0.0.1:5000/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question: userMessage, session_id: sessionId }),
        });
    
        if (!response.ok) {
          throw new Error("Error connecting to the server.");
        }
    
        const data = await response.json();
    
        // Update session ID
        sessionId = data.session_id;
        localStorage.setItem("session_id", sessionId);
    
        // Append assistant's response
        if (data.conversation) {
          const lastMessage = data.conversation[data.conversation.length - 1];
          appendMessage(lastMessage.role, lastMessage.content);
        }
    
        // Optionally display sources
        if (data.sources) {
          data.sources.forEach((source) => {
            appendMessage("Bot", `Source: ${source.title} (${source.url})`);
          });
        }
      } catch (error) {
        appendMessage("Bot", "Error: Could not connect to the server.");
      }
    }
  }
});
