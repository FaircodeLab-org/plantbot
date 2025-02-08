// Updated Chatbot JavaScript

document.addEventListener('DOMContentLoaded', function () {
  // Inject the chatbot widget into the body
  var chatbotHTML = `
  <!-- Include Font Awesome -->
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">

  <!-- Chatbot Widget HTML -->
  <div id="chatbot-widget">
    <!-- Chatbot Toggle Button -->
    <button id="chatbot-toggle" class="chatbot-toggle-button" aria-label="Open Chat">
      <i class="fas fa-comment-dots"></i>
    </button>
    <!-- Chatbot Container -->
    <div class="chatbot-container" id="chatbot-container">
      <!-- Chatbot Header -->
      <div class="chatbot-header">
        <div class="header-left">
          <div class="assistant-avatar">
            <img src="/assets/plantbot/images/assistant-avatar.png" alt="Assistant Avatar">
            <div class="online-indicator"></div>
          </div>
          <div class="assistant-info">
            <h3>Plantbot</h3>
            <p>Online</p>
          </div>
        </div>
        <div class="header-right">
          <button id="chatbot-minimize" class="chatbot-header-button" aria-label="Minimize Chat">
            <i class="fas fa-window-minimize"></i>
          </button>
          <button id="chatbot-close" class="chatbot-header-button" aria-label="Close Chat">
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>
      <!-- Chat Window -->
      <div id="chat-window">
        <!-- Chat messages will appear here -->
      </div>
      <!-- Input Container -->
      <form id="chat-form" class="input-container">
        <!-- New Image Upload Button -->
        <input type="file" id="image-input" accept="image/*" style="display: none;" />
        <button type="button" id="image-button" class="image-button" aria-label="Upload Image">
          <i class="fas fa-image"></i>
        </button>

        <!-- Existing Text Input -->
        <input type="text" id="user-input" placeholder="Type a message or upload an image..." autocomplete="off" />

        <!-- Voice Input Button -->
        <button type="button" id="voice-button" class="voice-button" aria-label="Voice Input">
          <i class="fas fa-microphone-alt"></i>
        </button>
        <!-- Send Button -->
        <button type="submit" id="send-button" class="send-button" aria-label="Send Message">
          <i class="fas fa-paper-plane"></i>
        </button>
      </form>
    </div>
  </div>
  `;

  // Append the chatbot widget to the body
  document.body.insertAdjacentHTML('beforeend', chatbotHTML);

  // Elements
  var sendButton = document.getElementById('send-button');
  var voiceButton = document.getElementById('voice-button');
  var imageButton = document.getElementById('image-button');
  var imageInput = document.getElementById('image-input');
  var userInputField = document.getElementById('user-input');
  var chatWindow = document.getElementById('chat-window');
  var chatbotToggle = document.getElementById('chatbot-toggle');
  var chatbotContainer = document.getElementById('chatbot-container');
  var chatbotClose = document.getElementById('chatbot-close');
  var chatbotMinimize = document.getElementById('chatbot-minimize');
  var chatForm = document.getElementById('chat-form');
  var isMinimized = false;
  var isRecording = false;
  var isTyping = false;

  // Toggle chatbot visibility
  chatbotToggle.onclick = function () {
    chatbotContainer.classList.add('active');
    chatbotToggle.style.display = 'none';
    isMinimized = false;

    // Display welcome message only once
    if (!chatWindow.dataset.hasWelcome) {
      var welcomeMessage = document.createElement('div');
      welcomeMessage.className = 'bot-message message';
      welcomeMessage.innerHTML = '🌿 Hello! I\'m your assistant from Plantrich Agritech Private Limited. How can I help you today?';
      chatWindow.appendChild(welcomeMessage);
      appendTimestamp(welcomeMessage);
      chatWindow.dataset.hasWelcome = 'true';
      chatWindow.scrollTop = chatWindow.scrollHeight;
    }
  };

  // Close chatbot
  chatbotClose.onclick = function () {
    chatbotContainer.classList.remove('active');
    chatbotToggle.style.display = 'block';
  };

  // Minimize chatbot
  chatbotMinimize.onclick = function () {
    if (!isMinimized) {
      chatbotContainer.classList.add('minimized');
      isMinimized = true;
      // Change icon to window-maximize
      chatbotMinimize.innerHTML = '<i class="fas fa-window-maximize"></i>';
      chatbotMinimize.setAttribute('aria-label', 'Maximize Chat');
    } else {
      chatbotContainer.classList.remove('minimized');
      isMinimized = false;
      // Change icon back to window-minimize
      chatbotMinimize.innerHTML = '<i class="fas fa-window-minimize"></i>';
      chatbotMinimize.setAttribute('aria-label', 'Minimize Chat');
    }
  };

  // Send button click event
  chatForm.addEventListener('submit', function (e) {
    e.preventDefault();
    sendMessage();
  });

  // Voice input button click event
  voiceButton.onclick = function () {
    startVoiceRecognition();
  };

  // Image upload button click event
  imageButton.onclick = function () {
    // Trigger the hidden file input when the image button is clicked
    imageInput.click();
  };

  // Handle image selection
  imageInput.onchange = function () {
    var file = imageInput.files[0];
    if (file) {
      // Display the selected image in the chat window
      displayUserImage(file);

      // Send the image to the server for processing
      sendImage(file);

      // Reset the input
      imageInput.value = '';
    }
  };

  function sendMessage() {
    var userInput = userInputField.value.trim();
    if (userInput === '') return;

    var currentTime = new Date();

    // Display user's message
    var userMessage = document.createElement('div');
    userMessage.className = 'user-message message';
    userMessage.innerHTML = userInput;
    chatWindow.appendChild(userMessage);
    appendTimestamp(userMessage);

    // Clear input
    userInputField.value = '';

    // Scroll to bottom
    chatWindow.scrollTop = chatWindow.scrollHeight;

    // Show typing indicator
    showTypingIndicator();

    // Call backend to get response
    frappe.call({
      method: 'plantbot.api.get_bot_response',
      args: {
        'user_message': userInput
      },
      callback: function (r) {
        // Remove typing indicator
        hideTypingIndicator();

        if (r.message) {
          var botMessage = document.createElement('div');
          botMessage.className = 'bot-message message';
          botMessage.innerHTML = r.message;
          chatWindow.appendChild(botMessage);
          appendTimestamp(botMessage);

          // Scroll to bottom
          chatWindow.scrollTop = chatWindow.scrollHeight;
        }
      },
      error: function (e) {
        // Remove typing indicator
        hideTypingIndicator();

        var botMessage = document.createElement('div');
        botMessage.className = 'bot-message message';
        botMessage.innerHTML = 'Sorry, an error occurred.';
        chatWindow.appendChild(botMessage);
        appendTimestamp(botMessage);

        chatWindow.scrollTop = chatWindow.scrollHeight;
      }
    });
  }

  function sendImage(file) {
    // Show typing indicator
    showTypingIndicator();

    var formData = new FormData();
    formData.append('image', file);

    $.ajax({
      url: '/api/method/plantbot.api.process_image',
      type: 'POST',
      data: formData,
      headers: {
        'X-Frappe-CSRF-Token': frappe.csrf_token
      },
      processData: false,
      contentType: false,
      success: function (r) {
        // Remove typing indicator
        hideTypingIndicator();

        if (r.message) {
          var botMessage = document.createElement('div');
          botMessage.className = 'bot-message message';
          botMessage.innerHTML = r.message;
          chatWindow.appendChild(botMessage);
          appendTimestamp(botMessage);

          // Scroll to bottom
          chatWindow.scrollTop = chatWindow.scrollHeight;
        }
      },
      error: function (e) {
        // Remove typing indicator
        hideTypingIndicator();

        var botMessage = document.createElement('div');
        botMessage.className = 'bot-message message';
        botMessage.innerHTML = 'Sorry, an error occurred.';
        chatWindow.appendChild(botMessage);
        appendTimestamp(botMessage);

        chatWindow.scrollTop = chatWindow.scrollHeight;
      }
    });
  }

  function displayUserImage(file) {
    var reader = new FileReader();
    reader.onload = function (e) {
      var userMessage = document.createElement('div');
      userMessage.className = 'user-message message';

      // Create an image element
      var img = document.createElement('img');
      img.src = e.target.result;
      img.style.maxWidth = '200px';
      img.style.borderRadius = '10px';

      userMessage.appendChild(img);
      chatWindow.appendChild(userMessage);
      appendTimestamp(userMessage);
      chatWindow.scrollTop = chatWindow.scrollHeight;
    };
    reader.readAsDataURL(file);
  }

  function formatTime(date) {
    var hours = date.getHours();
    var minutes = date.getMinutes();
    var ampm = hours >= 12 ? 'PM' : 'AM';

    hours = hours % 12;
    hours = hours || 12;
    minutes = minutes < 10 ? '0' + minutes : minutes;

    var strTime = hours + ':' + minutes + ' ' + ampm;
    return strTime;
  }

  function appendTimestamp(messageElement) {
    var timestamp = document.createElement('span');
    timestamp.className = 'timestamp';
    timestamp.textContent = formatTime(new Date());
    messageElement.appendChild(timestamp);
  }

  // Voice recognition function using Web Speech API
  function startVoiceRecognition() {
    if (!('webkitSpeechRecognition' in window)) {
      alert('Your browser does not support voice recognition. Please use Google Chrome.');
      return;
    }

    if (isRecording) {
      // If already recording, stop the recognition
      recognition.stop();
      isRecording = false;
      voiceButton.innerHTML = '<i class="fas fa-microphone-alt"></i>';
      voiceButton.classList.remove('is-recording');
      return;
    }

    isRecording = true;
    voiceButton.innerHTML = '<i class="fas fa-stop-circle"></i>';
    voiceButton.classList.add('is-recording');

    var recognition = new webkitSpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.start();

    recognition.onstart = function () {
      console.log('Voice recognition started. Try speaking into the microphone.');
    };

    recognition.onresult = function (event) {
      var transcript = event.results[0][0].transcript;
      userInputField.value = transcript;
      sendMessage();
    };

    recognition.onerror = function (event) {
      console.error('Voice recognition error:', event.error);
      isRecording = false;
      voiceButton.innerHTML = '<i class="fas fa-microphone-alt"></i>';
      voiceButton.classList.remove('is-recording');
    };

    recognition.onend = function () {
      console.log('Voice recognition ended.');
      isRecording = false;
      voiceButton.innerHTML = '<i class="fas fa-microphone-alt"></i>';
      voiceButton.classList.remove('is-recording');
    };
  }

  function showTypingIndicator() {
    if (isTyping) return;
    isTyping = true;
    var typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.id = 'typing-indicator';
    typingIndicator.innerHTML = '<i class="fas fa-ellipsis-h"></i> Plantbot is typing...';
    chatWindow.appendChild(typingIndicator);
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }

  function hideTypingIndicator() {
    isTyping = false;
    var indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
  }
});