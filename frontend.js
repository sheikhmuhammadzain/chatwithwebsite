(function() {
    // Prevent double injection
    if (window.__myChatBotLoaded) {
      console.log("Chat bot already loaded. Skipping initialization.");
      return;
    }
    window.__myChatBotLoaded = true;
    
    console.log("Website Chat Bot loading...");
  
    // --- Configuration --- (Easy to customize)
    const config = {
      botName: 'Website Chat Assistant',
      welcomeMessage: 'Hello! I can answer questions about this website. What would you like to know?',
      apiEndpoint: 'https://chatwithwebsite-lyart.vercel.app/api/chat',
      debug: true, // Enable debug mode
      // Colors (Feel free to change these)
      primaryColor: '#007AFF', // A modern blue
      headerGradient: 'linear-gradient(135deg, #007AFF, #0056b3)', // Header gradient
      userBubbleColor: '#007AFF',
      userTextColor: '#FFFFFF',
      botBubbleColor: '#f1f1f1',
      botTextColor: '#333333',
      containerBackground: '#FFFFFF',
      inputBackground: '#FFFFFF',
      inputTextColor: '#333333',
      buttonHoverBackground: '#0056b3',
      // Dimensions
      chatWidth: '350px',
      chatHeight: '450px', // Total height
      inputHeight: '50px', // Height of the input area
      // Font
      fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, Cantarell, "Fira Sans", "Droid Sans", "Helvetica Neue", sans-serif',
    };
    // --- End Configuration ---
  
    // Create styles
    const style = document.createElement('style');
    style.innerHTML = `
      :root {
        --cb-primary-color: ${config.primaryColor};
        --cb-header-gradient: ${config.headerGradient};
        --cb-user-bubble-color: ${config.userBubbleColor};
        --cb-user-text-color: ${config.userTextColor};
        --cb-bot-bubble-color: ${config.botBubbleColor};
        --cb-bot-text-color: ${config.botTextColor};
        --cb-container-bg: ${config.containerBackground};
        --cb-input-bg: ${config.inputBackground};
        --cb-input-text-color: ${config.inputTextColor};
        --cb-button-hover-bg: ${config.buttonHoverBackground};
        --cb-font-family: ${config.fontFamily};
        --cb-chat-width: ${config.chatWidth};
        --cb-chat-height: ${config.chatHeight};
        --cb-input-height: ${config.inputHeight};
      }
  
      #chatbot-container {
        position: fixed;
        bottom: 25px;
        right: 25px;
        width: var(--cb-chat-width);
        height: var(--cb-chat-height);
        background: var(--cb-container-bg);
        border: none; /* Remove default border */
        box-shadow: 0 5px 25px rgba(0, 0, 0, 0.15); /* Softer, more spread shadow */
        border-radius: 15px; /* Slightly larger radius */
        overflow: hidden;
        font-family: var(--cb-font-family);
        z-index: 9999;
        display: flex;
        flex-direction: column;
        transition: all 0.3s ease-in-out; /* For potential future animations */
      }
  
      #chatbot-header {
        background: var(--cb-header-gradient);
        color: white;
        padding: 15px 20px; /* Increased padding */
        text-align: center;
        font-size: 1.1em; /* Slightly larger font */
        font-weight: 600; /* Bolder font */
        flex-shrink: 0; /* Prevent header from shrinking */
        border-bottom: 1px solid rgba(0, 0, 0, 0.05); /* Subtle separator */
        display: flex; /* Use flex for alignment */
        justify-content: center; /* Center title */
        align-items: center;
        gap: 8px; /* Space between icon and text */
      }
  
      #chatbot-header svg { /* Style for potential header icon */
          width: 20px;
          height: 20px;
          fill: white;
      }
  
      #chatbot-messages {
        flex-grow: 1; /* Take available space */
        overflow-y: auto;
        padding: 20px 15px; /* More vertical padding */
        background-color: #f9f9f9; /* Slightly off-white background for messages */
        scrollbar-width: thin; /* Firefox */
        scrollbar-color: #ccc #f1f1f1; /* Firefox */
      }
  
      /* Webkit Scrollbar Styles */
      #chatbot-messages::-webkit-scrollbar {
        width: 6px;
      }
      #chatbot-messages::-webkit-scrollbar-track {
        background: #f1f1f1;
        border-radius: 3px;
      }
      #chatbot-messages::-webkit-scrollbar-thumb {
        background: #ccc;
        border-radius: 3px;
      }
      #chatbot-messages::-webkit-scrollbar-thumb:hover {
        background: #aaa;
      }
  
      .chatbot-message { /* Container for alignment */
        margin-bottom: 12px; /* Increased spacing */
        display: flex;
      }
  
      .chatbot-message.user {
        justify-content: flex-end; /* Align user messages to the right */
      }
  
      .chatbot-message.bot {
        justify-content: flex-start; /* Align bot messages to the left */
      }
  
      .message-bubble {
        padding: 10px 15px; /* Increased padding */
        border-radius: 18px; /* Pill shape */
        font-size: 0.95em; /* Slightly adjusted font size */
        line-height: 1.4;
        max-width: 85%; /* Allow slightly wider messages */
        word-wrap: break-word; /* Ensure long words break */
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); /* Subtle shadow on bubbles */
      }
  
      .chatbot-message.user .message-bubble {
        background: var(--cb-user-bubble-color);
        color: var(--cb-user-text-color);
        border-bottom-right-radius: 5px; /* Slightly different radius for user */
      }
  
      .chatbot-message.bot .message-bubble {
        background: var(--cb-bot-bubble-color);
        color: var(--cb-bot-text-color);
        border-bottom-left-radius: 5px; /* Slightly different radius for bot */
      }

      /* Typing indicator */
      .typing-indicator {
        padding: 10px 15px;
        display: flex;
        align-items: center;
        background: var(--cb-bot-bubble-color);
        border-radius: 18px;
        border-bottom-left-radius: 5px;
        max-width: 85%;
        margin-bottom: 12px;
      }
      
      .typing-indicator span {
        height: 8px;
        width: 8px;
        float: left;
        margin: 0 1px;
        background-color: #9E9EA1;
        display: block;
        border-radius: 50%;
        opacity: 0.4;
      }
      
      .typing-indicator span:nth-of-type(1) {
        animation: 1s blink infinite 0.3333s;
      }
      
      .typing-indicator span:nth-of-type(2) {
        animation: 1s blink infinite 0.6666s;
      }
      
      .typing-indicator span:nth-of-type(3) {
        animation: 1s blink infinite 0.9999s;
      }
      
      @keyframes blink {
        50% {
          opacity: 1;
        }
      }
  
      #chatbot-input-container { /* Renamed for clarity */
        display: flex;
        align-items: center; /* Vertically align items */
        padding: 10px 15px; /* Padding around input and button */
        border-top: 1px solid #e0e0e0; /* Softer border */
        background: var(--cb-input-bg);
        min-height: var(--cb-input-height); /* Ensure consistent height */
        box-sizing: border-box; /* Include padding in height calculation */
        flex-shrink: 0; /* Prevent input area from shrinking */
      }
  
      #chatbot-input-container input {
        flex: 1; /* Take available space */
        padding: 10px 15px; /* Comfortable padding */
        border: 1px solid #dcdcdc; /* Subtle border */
        border-radius: 20px; /* Rounded input field */
        outline: none;
        font-size: 0.95em;
        color: var(--cb-input-text-color);
        background-color: var(--cb-input-bg);
        margin-right: 10px; /* Space between input and button */
        transition: border-color 0.2s ease;
      }
      #chatbot-input-container input:focus {
        border-color: var(--cb-primary-color); /* Highlight on focus */
      }
      #chatbot-input-container input::placeholder {
          color: #aaa;
      }
  
      #chatbot-send-button { /* Renamed for clarity */
        padding: 0; /* Remove padding, rely on width/height */
        border: none;
        background: var(--cb-primary-color);
        color: white;
        cursor: pointer;
        border-radius: 50%; /* Circular button */
        width: 36px; /* Fixed size */
        height: 36px;
        flex-shrink: 0; /* Prevent button from shrinking */
        display: flex;
        align-items: center;
        justify-content: center;
        transition: background-color 0.2s ease;
      }
      #chatbot-send-button:hover {
        background: var(--cb-button-hover-bg);
      }
      #chatbot-send-button svg {
        width: 18px;
        height: 18px;
        fill: white;
        /* Correct potential alignment issues */
        display: block;
         /* SVG specific transform if needed for centering */
        transform: translateX(1px);
      }
      #chatbot-send-button:disabled {
          background-color: #b0b0b0;
          cursor: not-allowed;
      }
    `;
    document.head.appendChild(style);
  
    // Create chatbot container
    const container = document.createElement('div');
    container.id = 'chatbot-container';
  
    // SVG for Send Icon (Paper plane)
    const sendIconSVG = `
      <svg viewBox="0 0 24 24" fill="currentColor">
        <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
      </svg>`;
  
    // SVG for Bot Icon (Simple Robot Head)
    const botIconSVG = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" width="24px" height="24px"><path d="M0 0h24v24H0V0z" fill="none"/><path d="M19 6h-4V4c0-1.1-.9-2-2-2h-4c-1.1 0-2 .9-2 2v2H3c-1.1 0-2 .9-2 2v11c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-5 0h-4V4h4v2zM4 19V9h16v10H4zm4-6c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2zm8 0c1.1 0 2 .9 2 2s-.9 2-2 2-2-.9-2-2 .9-2 2-2z"/></svg>
    `;
  
  
    container.innerHTML = `
      <div id="chatbot-header">
          ${botIconSVG}
          <span>${config.botName}</span>
      </div>
      <div id="chatbot-messages"></div>
      <div id="chatbot-input-container">
        <input type="text" placeholder="Type a message..." />
        <button id="chatbot-send-button" title="Send Message">
          ${sendIconSVG}
        </button>
      </div>
    `;
    document.body.appendChild(container);
  
    // Get references to the new elements
    const messagesContainer = container.querySelector('#chatbot-messages');
    const inputField = container.querySelector('#chatbot-input-container input');
    const sendButton = container.querySelector('#chatbot-send-button');
  
    // Function to append a message to the chat
    function appendMessage(text, from = 'user') {
      const messageWrapper = document.createElement('div');
      messageWrapper.classList.add('chatbot-message', from); // 'user' or 'bot'
  
      const messageBubble = document.createElement('div');
      messageBubble.classList.add('message-bubble');
      
      // Allow HTML in bot messages for formatting
      if (from === 'bot') {
        messageBubble.innerHTML = text;
      } else {
        messageBubble.textContent = text; // Plain text for user messages
      }
  
      messageWrapper.appendChild(messageBubble);
      messagesContainer.appendChild(messageWrapper);
  
      // Scroll to the bottom
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  
    // Add initial bot welcome message
    setTimeout(() => {
        if (config.welcomeMessage) {
            appendMessage(config.welcomeMessage, 'bot');
        }
    }, 500); // Slight delay for effect
  
  
    // --- Bot Logic ---
    let typingIndicator = null;
    
    function showTypingIndicator() {
        // Create typing indicator if it doesn't exist
        if (!typingIndicator) {
            typingIndicator = document.createElement('div');
            typingIndicator.className = 'typing-indicator';
            typingIndicator.innerHTML = '<span></span><span></span><span></span>';
            
            const wrapper = document.createElement('div');
            wrapper.className = 'chatbot-message bot';
            wrapper.appendChild(typingIndicator);
            
            messagesContainer.appendChild(wrapper);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        // Disable input while typing
        inputField.disabled = true;
        sendButton.disabled = true;
    }
  
    function hideTypingIndicator() {
       if (typingIndicator) {
           const wrapper = typingIndicator.parentNode;
           if (wrapper) {
               messagesContainer.removeChild(wrapper);
           }
           typingIndicator = null;
       }
       
       inputField.disabled = false;
       sendButton.disabled = false;
       inputField.focus(); // Return focus to input
    }
  
    // Get bot reply from the API
    async function getBotReply(userText) {
        const currentUrl = window.location.href;
        console.log(`Sending request to ${config.apiEndpoint} for website: ${currentUrl}`);
        
        try {
            const response = await fetch(config.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    url: currentUrl,
                    message: userText,
                    debug: config.debug
                })
            });
            
            if (!response.ok) {
                throw new Error(`API error: ${response.status} ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log("API response:", data);
            
            // Log debug info if available
            if (data.debug_info) {
                console.log("Debug info:", data.debug_info);
            }
            
            return data.response;
        } catch (error) {
            console.error("Error calling chat API:", error);
            return "Sorry, I encountered an error while processing your request. The API might be experiencing issues. Please try again later.";
        }
    }
  
    async function handleSend() {
      const text = inputField.value.trim();
      if (!text) return;
  
      appendMessage(text, 'user');
      inputField.value = ''; // Clear input immediately
  
      showTypingIndicator();
  
      try {
          const botResponse = await getBotReply(text);
          hideTypingIndicator();
          appendMessage(botResponse, 'bot');
      } catch (error) {
          console.error("Bot Error:", error);
          hideTypingIndicator();
          appendMessage("Sorry, I encountered an error. Please try again.", 'bot');
      }
    }
  
    // --- Event Listeners ---
    sendButton.onclick = handleSend;
  
    inputField.addEventListener('keypress', (e) => {
      // Check if Enter key was pressed without Shift key
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault(); // Prevent default newline behavior
        handleSend();
      }
    });
    
    console.log(`Website Chat Bot loaded successfully for ${window.location.href}`);
  
  })();