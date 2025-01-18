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
  width: 400px;
  height: 600px;
  background: white;
  border-radius: 15px;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  z-index: 10000;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  display: flex;
  flex-direction: column;
`;

chatBox.innerHTML = `
  <div style="padding: 20px; display: flex; flex-direction: column; height: 100%;">
    <div id="chat-content" style="flex: 1; overflow-y: auto; margin-bottom: 20px; padding-right: 10px;">
      <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 20px;">
        <div style="width: 32px; height: 32px;">
          <svg viewBox="0 0 32 32" style="width: 100%; height: 100%; fill: #0078d7;">
            <path d="M16 4l12 7v10l-12 7-12-7V11l12-7z"/>
          </svg>
        </div>
        <div>
          <h2 style="margin: 0; font-size: 16px;">Hi!</h2>
          <p style="margin: 5px 0 0; color: #666; font-size: 14px;">I'm an AI assistant trained on documentation, help articles, and other content.</p>
        </div>
      </div>
      
      <p style="margin: 15px 0; font-size: 14px;">Ask me anything about <span style="background: #0078d7; color: white; padding: 2px 8px; border-radius: 4px;">Your Product</span>.</p>
      
      <div style="margin: 20px 0;">
        <p style="color: #666; font-size: 12px; margin-bottom: 10px;">EXAMPLE QUESTIONS</p>
        <div style="display: flex; flex-wrap: wrap; gap: 10px;">
          <button class="example-question" style="border: 1px solid #ddd; background: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; font-size: 13px;">What's new in version 2.5?</button>
          <button class="example-question" style="border: 1px solid #ddd; background: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; font-size: 13px;">How to use full text search?</button>
          <button class="example-question" style="border: 1px solid #ddd; background: none; padding: 8px 15px; border-radius: 20px; cursor: pointer; font-size: 13px;">How do I perform hybrid search?</button>
        </div>
      </div>
    </div>
    
    <div style="flex-shrink: 0;">
      <input id="chat-input" type="text" placeholder="Type your question..." style="width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 14px; box-sizing: border-box;" />
    </div>
  </div>
`;

document.body.appendChild(chatBox);

function appendMessage(role, content, sources = null) {
  const messageElem = document.createElement("div");
  messageElem.style.cssText = "margin-bottom: 15px; font-size: 14px;";
  
  const avatar = document.createElement("div");
  avatar.style.cssText = "display: inline-block; width: 24px; height: 24px; margin-right: 8px; vertical-align: top;";
  avatar.innerHTML = role === "You" ? 
    '<svg viewBox="0 0 24 24" style="width: 100%; height: 100%; fill: #666;"><circle cx="12" cy="12" r="12"/></svg>' :
    '<svg viewBox="0 0 24 24" style="width: 100%; height: 100%; fill: #0078d7;"><path d="M12 2l8 5v10l-8 5-8-5V7l8-5z"/></svg>';
  
  const messageContent = document.createElement("div");
  messageContent.style.cssText = "display: inline-block; max-width: calc(100% - 40px);";
  messageContent.textContent = content;

  messageElem.appendChild(avatar);
  messageElem.appendChild(messageContent);

  // Add sources if provided
  if (sources) {
    const sourcesContainer = document.createElement("div");
    sourcesContainer.style.cssText = "margin-top: 10px; margin-left: 32px; font-size: 12px; color: #666;";
    sources.forEach(source => {
      const sourceLink = document.createElement("a");
      sourceLink.href = source.url;
      sourceLink.target = "_blank";
      sourceLink.style.cssText = "display: block; margin-bottom: 5px; color: #0078d7; text-decoration: none;";
      sourceLink.innerHTML = `📄 ${source.title}`;
      sourcesContainer.appendChild(sourceLink);
    });
    messageElem.appendChild(sourcesContainer);
  }

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

// Add example question click handlers
document.querySelectorAll('.example-question').forEach(button => {
  button.addEventListener('click', () => {
    const question = button.textContent;
    document.getElementById('chat-input').value = question;
    // Trigger an Enter keypress event
    document.getElementById('chat-input').dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter' }));
  });
});
