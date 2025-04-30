// This script bypasses website scraping by sending the current page's content directly
// Paste in browser console to use

(function() {
  if (window.__chatProxyLoaded) {
    console.log("Chat proxy already loaded.");
    return;
  }
  window.__chatProxyLoaded = true;
  
  // Extract text content from the current page
  function extractPageContent() {
    const bodyText = document.body.innerText;
    // Limit to ~10K characters to prevent overwhelming the API
    return bodyText.slice(0, 10000);
  }
  
  // Configuration
  const config = {
    botName: 'Website Assistant',
    apiKey: prompt("Enter your OpenAI API key:", ""),
    model: "gpt-4o-mini", // or gpt-3.5-turbo for faster responses
    temperature: 0.3,
  };
  
  if (!config.apiKey) {
    alert("API key is required to use this chat assistant");
    return;
  }
  
  // Create UI
  const uiHTML = `
    <div id="proxy-chat-container">
      <div id="proxy-chat-header">
        <span>💬 ${config.botName}</span>
        <button id="proxy-chat-close">×</button>
      </div>
      <div id="proxy-chat-messages"></div>
      <div id="proxy-chat-input">
        <textarea placeholder="Ask about this page..."></textarea>
        <button id="proxy-chat-send">Send</button>
      </div>
    </div>
  `;
  
  // Add styles
  const styleEl = document.createElement('style');
  styleEl.innerHTML = `
    #proxy-chat-container {
      position: fixed;
      bottom: 20px;
      right: 20px;
      width: 350px;
      height: 500px;
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.2);
      display: flex;
      flex-direction: column;
      z-index: 10000;
      font-family: system-ui, -apple-system, sans-serif;
    }
    #proxy-chat-header {
      padding: 15px;
      background: #007AFF;
      color: white;
      border-radius: 12px 12px 0 0;
      font-weight: bold;
      display: flex;
      justify-content: space-between;
    }
    #proxy-chat-close {
      background: none;
      border: none;
      color: white;
      font-size: 20px;
      cursor: pointer;
    }
    #proxy-chat-messages {
      flex: 1;
      overflow-y: auto;
      padding: 15px;
      background: #f7f7f7;
    }
    .proxy-chat-message {
      margin-bottom: 10px;
      padding: 10px;
      border-radius: 10px;
      max-width: 80%;
    }
    .proxy-chat-user {
      background: #007AFF;
      color: white;
      margin-left: auto;
    }
    .proxy-chat-bot {
      background: #e5e5ea;
      color: black;
    }
    #proxy-chat-input {
      padding: 10px;
      border-top: 1px solid #eee;
      display: flex;
    }
    #proxy-chat-input textarea {
      flex: 1;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 16px;
      resize: none;
      height: 20px;
      outline: none;
    }
    #proxy-chat-send {
      width: 60px;
      margin-left: 8px;
      background: #007AFF;
      color: white;
      border: none;
      border-radius: 16px;
      cursor: pointer;
    }
    #proxy-chat-send:hover {
      background: #0056b3;
    }
  `;
  
  document.head.appendChild(styleEl);
  
  // Create container
  const container = document.createElement('div');
  container.innerHTML = uiHTML;
  document.body.appendChild(container);
  
  // Get elements
  const messagesEl = document.getElementById('proxy-chat-messages');
  const inputEl = document.querySelector('#proxy-chat-input textarea');
  const sendButton = document.getElementById('proxy-chat-send');
  const closeButton = document.getElementById('proxy-chat-close');
  
  // Extract page content immediately
  const pageContent = extractPageContent();
  console.log(`Extracted ${pageContent.length} characters from the current page`);
  
  // Add a message to the chat
  function addMessage(text, isUser) {
    const messageEl = document.createElement('div');
    messageEl.className = `proxy-chat-message ${isUser ? 'proxy-chat-user' : 'proxy-chat-bot'}`;
    messageEl.textContent = text;
    messagesEl.appendChild(messageEl);
    messagesEl.scrollTop = messagesEl.scrollHeight;
  }
  
  // Show initial message
  addMessage("Hello! I can answer questions about this page. What would you like to know?", false);
  
  // Send message to OpenAI API
  async function sendToAPI(userMessage) {
    try {
      const response = await fetch('https://api.openai.com/v1/chat/completions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${config.apiKey}`
        },
        body: JSON.stringify({
          model: config.model,
          messages: [
            {
              role: "system",
              content: `You are a helpful assistant that answers questions about a webpage. 
              Use ONLY the following content from the page to answer questions.
              If you don't find the information in the content, say "I don't see that information on this page."
              
              PAGE CONTENT:
              ${pageContent}`
            },
            { role: "user", content: userMessage }
          ],
          temperature: config.temperature
        })
      });
      
      const data = await response.json();
      if (data.error) {
        throw new Error(data.error.message);
      }
      
      return data.choices[0].message.content;
    } catch (error) {
      console.error("Error calling OpenAI API:", error);
      return "Sorry, I encountered an error. Please try again.";
    }
  }
  
  // Handle sending messages
  async function handleSend() {
    const text = inputEl.value.trim();
    if (!text) return;
    
    // Add user message
    addMessage(text, true);
    inputEl.value = '';
    
    // Disable input while waiting
    inputEl.disabled = true;
    sendButton.disabled = true;
    
    // Get response
    const response = await sendToAPI(text);
    
    // Add bot message
    addMessage(response, false);
    
    // Re-enable input
    inputEl.disabled = false;
    sendButton.disabled = false;
    inputEl.focus();
  }
  
  // Event listeners
  sendButton.addEventListener('click', handleSend);
  
  inputEl.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  });
  
  closeButton.addEventListener('click', () => {
    container.remove();
    styleEl.remove();
    window.__chatProxyLoaded = false;
  });
  
  // Focus the input field
  inputEl.focus();
  
  console.log("Website Chat Proxy loaded successfully!");
})(); 