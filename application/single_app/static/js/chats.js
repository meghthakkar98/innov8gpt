// Application state
let personalDocs = [];
let groupDocs = [];
let activeGroupName = "";
let currentConversationId = null;
let userPrompts = [];
let groupPrompts = [];
let activeGroupId = null; // Define activeGroupId variable

/*************************************************
 *  LOADING PROMPTS
 *************************************************/

const promptSelect = document.getElementById("prompt-select");

function loadUserPrompts() {
  return fetch("/api/prompts")
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.prompts) {
        userPrompts = data.prompts;
      }
    })
    .catch(err => console.error("Error loading user prompts:", err));
}

function loadGroupPrompts() {
  return fetch("/api/group_prompts")
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then(data => {
      if (data.prompts) {
        groupPrompts = data.prompts;
      }
    })
    .catch(err => console.error("Error loading group prompts:", err));
}

function populatePromptSelect() {
  if (!promptSelect) return;

  promptSelect.innerHTML = "";
  const defaultOpt = document.createElement("option");
  defaultOpt.value = "";
  defaultOpt.textContent = "Select a Prompt...";
  promptSelect.appendChild(defaultOpt);

  // Combine userPrompts + groupPrompts
  const combined = [
    ...userPrompts.map(p => ({...p, scope: "User"})),
    ...groupPrompts.map(p => ({...p, scope: "Group"}))
  ];

  combined.forEach(promptObj => {
    const opt = document.createElement("option");
    opt.value = promptObj.id;
    opt.textContent = `[${promptObj.scope}] ${promptObj.name}`;
    opt.dataset.promptContent = promptObj.content;
    promptSelect.appendChild(opt);
  });
}

// Toggle show/hide
const searchPromptsBtn = document.getElementById("search-prompts-btn");
const userInput = document.getElementById("user-input"); // Define userInput here
if (searchPromptsBtn) {
  searchPromptsBtn.addEventListener("click", function() {
    if (!promptSelect || !userInput) return;

    const isActive = this.classList.toggle("active");

    if (isActive) {
      // Hide the text input
      userInput.style.display = "none";

      // Show the prompt dropdown
      promptSelect.style.display = "inline-block";

      // (Re)populate the dropdown with any prompts
      populatePromptSelect();

      // Optionally, reset any previously entered text
      userInput.value = "";
    } else {
      // Show the text input
      userInput.style.display = "inline-block";

      // Hide the prompt dropdown
      promptSelect.style.display = "none";

      // Reset the prompt select back to default
      promptSelect.selectedIndex = 0;
    }
  });
}

/*************************************************
 *  LOAD / DISPLAY CONVERSATIONS
 *************************************************/
function loadConversations() {
  fetch("/api/get_conversations")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      const conversationsList = document.getElementById("conversations-list");
      if (!conversationsList) return;

      conversationsList.innerHTML = "";
      data.conversations.forEach((convo) => {
        const convoItem = document.createElement("div");
        convoItem.classList.add("list-group-item", "conversation-item");
        convoItem.setAttribute("data-conversation-id", convo.id);
        convoItem.setAttribute("data-conversation-title", convo.title);

        const date = new Date(convo.last_updated);
        convoItem.innerHTML = `
          <div class="d-flex justify-content-between align-items-center">
            <div>
              <span>${convo.title}</span><br>
              <small>${date.toLocaleString()}</small>
            </div>
            <button
              class="btn btn-danger btn-sm delete-btn"
              data-conversation-id="${convo.id}"
            >
              <i class="bi bi-trash"></i>
            </button>
          </div>
        `;
        conversationsList.appendChild(convoItem);
      });
    })
    .catch((error) => {
      console.error("Error loading conversations:", error);
    });
}

function addConversationToList(conversationId, title = null) {
  const conversationsList = document.getElementById("conversations-list");
  if (!conversationsList) return;

  const items = document.querySelectorAll(".conversation-item");
  items.forEach((i) => i.classList.remove("active"));

  const convoItem = document.createElement("div");
  convoItem.classList.add("list-group-item", "conversation-item", "active");
  convoItem.setAttribute("data-conversation-id", conversationId);
  convoItem.setAttribute("data-conversation-title", title || conversationId);

  const d = new Date();
  convoItem.innerHTML = `
    <div class="d-flex justify-content-between align-items-center">
      <div>
        <span>${title || conversationId}</span><br>
        <small>${d.toLocaleString()}</small>
      </div>
      <button
        class="btn btn-danger btn-sm delete-btn"
        data-conversation-id="${conversationId}"
      >
        <i class="bi bi-trash"></i>
      </button>
    </div>
  `;
  conversationsList.prepend(convoItem);
}

function updateConversationInList(conversationId, title) {
  if (!conversationId || !title) return;
  
  const convoItem = document.querySelector(
    `.conversation-item[data-conversation-id="${conversationId}"]`
  );
  
  if (convoItem) {
    const d = new Date();
    convoItem.innerHTML = `
      <div class="d-flex justify-content-between align-items-center">
        <div>
          <span>${title}</span><br>
          <small>${d.toLocaleString()}</small>
        </div>
        <button
          class="btn btn-danger btn-sm delete-btn"
          data-conversation-id="${conversationId}"
        >
          <i class="bi bi-trash"></i>
        </button>
      </div>
    `;
    convoItem.setAttribute("data-conversation-title", title);
  } else {
    // If the conversation doesn't exist in the list, add it
    addConversationToList(conversationId, title);
  }
}

/*************************************************
 *  DOC SCOPE & POPULATING SELECT
 *************************************************/
function populateDocumentSelectScope() {
  const scopeSel = document.getElementById("doc-scope-select");
  const docSel = document.getElementById("document-select");
  if (!scopeSel || !docSel) return;

  docSel.innerHTML = "";

  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "All Documents";
  docSel.appendChild(noneOpt);

  const scopeVal = scopeSel.value || "all";

  let finalDocs = [];
  if (scopeVal === "all") {
    const pDocs = personalDocs.map((d) => ({
      id: d.id,
      label: `[Personal] ${d.file_name}`,
    }));
    const gDocs = groupDocs.map((d) => ({
      id: d.id,
      label: `[Group: ${activeGroupName}] ${d.file_name}`,
    }));
    finalDocs = pDocs.concat(gDocs);
  } else if (scopeVal === "personal") {
    finalDocs = personalDocs.map((d) => ({
      id: d.id,
      label: `[Personal] ${d.file_name}`,
    }));
  } else if (scopeVal === "group") {
    finalDocs = groupDocs.map((d) => ({
      id: d.id,
      label: `[Group: ${activeGroupName}] ${d.file_name}`,
    }));
  }

  finalDocs.forEach((doc) => {
    const opt = document.createElement("option");
    opt.value = doc.id;
    opt.textContent = doc.label;
    docSel.appendChild(opt);
  });
}

const docScopeSelect = document.getElementById("doc-scope-select");
if (docScopeSelect) {
  docScopeSelect.addEventListener("change", populateDocumentSelectScope);
}

/*************************************************
 *  LOADING PERSONAL & GROUP DOCS
 *************************************************/
function loadPersonalDocs() {
  return fetch("/api/documents")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data.error) {
        console.warn("Error fetching user docs:", data.error);
        personalDocs = [];
        return;
      }
      personalDocs = data.documents || [];
    })
    .catch((err) => {
      console.error("Error loading personal docs:", err);
      personalDocs = [];
    });
}

function loadGroupDocs() {
  return fetch("/api/groups")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then((groups) => {
      const activeGroup = groups.find((g) => g.isActive);
      if (activeGroup) {
        activeGroupName = activeGroup.name || "Active Group";
        activeGroupId = activeGroup.id || null; // Set activeGroupId
        return fetch("/api/group_documents")
          .then((response) => {
            if (!response.ok) {
              throw new Error(`HTTP error ${response.status}`);
            }
            return response.json();
          })
          .then((data) => {
            if (data.error) {
              console.warn("Error fetching group docs:", data.error);
              groupDocs = [];
              return;
            }
            groupDocs = data.documents || [];
          })
          .catch((err) => {
            console.error("Error loading group docs:", err);
            groupDocs = [];
          });
      } else {
        activeGroupName = "";
        activeGroupId = null;
        groupDocs = [];
      }
    })
    .catch((err) => {
      console.error("Error loading groups:", err);
      groupDocs = [];
    });
}

function loadAllDocs() {
  const hasDocControls =
    document.getElementById("search-documents-btn") ||
    document.getElementById("doc-scope-select") ||
    document.getElementById("document-select");

  if (!hasDocControls) {
    return Promise.resolve();
  }

  return loadPersonalDocs().then(() => loadGroupDocs());
}

/*************************************************
 *  TOGGLE BUTTONS: SEARCH DOCUMENTS, WEB SEARCH, IMAGE GEN
 *************************************************/
const searchDocumentsBtn = document.getElementById("search-documents-btn");
if (searchDocumentsBtn) {
  searchDocumentsBtn.addEventListener("click", function () {
    this.classList.toggle("active");

    const docScopeSel = document.getElementById("doc-scope-select");
    const docSelectEl = document.getElementById("document-select");
    if (!docScopeSel || !docSelectEl) return;

    if (this.classList.contains("active")) {
      docScopeSel.style.display = "inline-block";
      docSelectEl.style.display = "inline-block";
      populateDocumentSelectScope();
    } else {
      docScopeSel.style.display = "none";
      docSelectEl.style.display = "none";
      docSelectEl.innerHTML = "";
    }
  });
}

const webSearchBtn = document.getElementById("search-web-btn");
if (webSearchBtn) {
  webSearchBtn.addEventListener("click", function () {
    this.classList.toggle("active");
  });
}

const imageGenBtn = document.getElementById("image-generate-btn");
if (imageGenBtn) {
  imageGenBtn.addEventListener("click", function () {
    this.classList.toggle("active");

    const isImageGenEnabled = this.classList.contains("active");
    const docBtn = document.getElementById("search-documents-btn");
    const webBtn = document.getElementById("search-web-btn");
    const fileBtn = document.getElementById("choose-file-btn");

    if (isImageGenEnabled) {
      if (docBtn) {
        docBtn.disabled = true;
        docBtn.classList.remove("active");
      }
      if (webBtn) {
        webBtn.disabled = true;
        webBtn.classList.remove("active");
      }
      if (fileBtn) {
        fileBtn.disabled = true;
        fileBtn.classList.remove("active");
      }
    } else {
      if (docBtn) docBtn.disabled = false;
      if (webBtn) webBtn.disabled = false;
      if (fileBtn) fileBtn.disabled = false;
    }
  });
}

/*************************************************
 *  SELECTING A CONVERSATION
 *************************************************/
function selectConversation(conversationId) {
  currentConversationId = conversationId;

  const convoItem = document.querySelector(
    `.conversation-item[data-conversation-id="${conversationId}"]`
  );
  const conversationTitle = convoItem
    ? convoItem.getAttribute("data-conversation-title")
    : "Conversation";

  const currentTitleEl = document.getElementById("current-conversation-title");
  if (currentTitleEl) {
    currentTitleEl.textContent = conversationTitle;
  }

  loadMessages(conversationId);
  highlightSelectedConversation(conversationId);
}

function highlightSelectedConversation(conversationId) {
  const items = document.querySelectorAll(".conversation-item");
  items.forEach((item) => {
    if (item.getAttribute("data-conversation-id") === conversationId) {
      item.classList.add("active");
    } else {
      item.classList.remove("active");
    }
  });
}

/*************************************************
 *  APPEND MESSAGE LOCALLY
 *************************************************/
function scrollChatToBottom() {
  const chatbox = document.getElementById("chatbox");
  if (chatbox) {
    chatbox.scrollTop = chatbox.scrollHeight;
  }
}

function appendMessage(sender, messageContent, modelName = null, messageId = null) {
  const chatbox = document.getElementById("chatbox");
  if (!chatbox) return;

  const messageDiv = document.createElement("div");
  messageDiv.classList.add("mb-2");

  let avatarImg = "";
  let avatarAltText = "";
  let messageClass = "";
  let senderLabel = "";
  let messageContentHtml = "";
  let feedbackHtml = "";

  if (sender === "System") {
    messageClass = "system-message"; // Ensure every sender has a class value
    senderLabel = "System";
    messageContentHtml = DOMPurify.sanitize(marked.parse(messageContent));
  } else if (sender === "safety") {
    messageClass = "ai-message";
    senderLabel = "Content Safety";
    avatarAltText = "Content Safety Avatar";
    avatarImg = "/static/images/alert.png";
    const linkToViolations = `
      <br>
      <small>
        <a href="/safety_violations" target="_blank" rel="noopener" style="font-size: 0.85em; color: #6c757d;">
          View My Safety Violations
        </a>
      </small>
    `;

    messageContentHtml = DOMPurify.sanitize(
      marked.parse(messageContent + linkToViolations)
    );
  } else if (sender === "image") {
    messageClass = "ai-message";
    senderLabel = modelName
      ? `AI <span style="color: #6c757d; font-size: 0.8em;">(${modelName})</span>`
      : "AI";
    avatarImg = "/static/images/ai-avatar.png";
    avatarAltText = "AI Avatar";

    const imageHtml = `
      <img 
        src="${messageContent}" 
        alt="Generated Image" 
        class="generated-image" 
        style="width: 25%; cursor: pointer;"
        data-image-src="${messageContent}"
        onload="scrollChatToBottom()"
      />
    `;
    messageContentHtml = imageHtml;
  } else if (sender === "You") {
    messageClass = "user-message";
    senderLabel = "You";
    avatarAltText = "User Avatar";
    avatarImg = "/static/images/user-avatar.png";
    messageContentHtml = DOMPurify.sanitize(marked.parse(messageContent));
  } else if (sender === "AI") {
    messageClass = "ai-message";
    avatarAltText = "AI Avatar";
    avatarImg = "/static/images/ai-avatar.png";
    senderLabel = modelName
      ? `AI <span style="color: #6c757d; font-size: 0.8em;">(${modelName})</span>`
      : "AI";

    feedbackHtml = renderFeedbackIcons(messageId, currentConversationId);

    let cleaned = messageContent.trim().replace(/\n{3,}/g, "\n\n");
    cleaned = cleaned.replace(/(\bhttps?:\/\/\S+)(%5D|\])+/gi, (_, url) => url);
    const withCitations = parseCitations(cleaned);
    const htmlContent = DOMPurify.sanitize(marked.parse(withCitations));
    messageContentHtml = htmlContent;
  } else if (sender === "File") {
    messageClass = "file-message";
    senderLabel = "File Added";
    const filename = messageContent.filename;
    const fileId = messageContent.file_id;
    messageContentHtml = `
      <a 
        href="#"
        class="file-link"
        data-conversation-id="${currentConversationId}"
        data-file-id="${fileId}"
      >
        ${filename}
      </a>
    `;
  } else if (sender === "Error") {
    messageClass = "error-message";
    senderLabel = "Error";
    messageContentHtml = DOMPurify.sanitize(marked.parse(messageContent));
  }

  // Add message class safely - fix for the DOMTokenList error
  messageDiv.classList.add("message");
  if (messageClass) {
    messageDiv.classList.add(messageClass);
  }

  messageDiv.innerHTML = `
    <div class="message-content ${
      sender === "You" || sender === "File" ? "flex-row-reverse" : ""
    }">
      ${
        sender !== "File"
          ? `<img src="${avatarImg}" alt="${avatarAltText}" class="avatar">`
          : ""
      }
      <div class="message-bubble">
        <div class="message-sender">${senderLabel}</div>
        <div class="message-text">${messageContentHtml}</div>
        ${feedbackHtml || ""}
      </div>
    </div>
  `;

  chatbox.appendChild(messageDiv);
  scrollChatToBottom();
}

/*************************************************
 *  LOADING MESSAGES FOR CONVERSATION
 *************************************************/
function loadMessages(conversationId) {
  fetch(`/conversation/${conversationId}/messages`)
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      
      const contentType = response.headers.get('content-type');
      if (!contentType || !contentType.includes('application/json')) {
        throw new TypeError(`Expected JSON but got ${contentType}`);
      }
      
      return response.json();
    })
    .then((data) => {
      const chatbox = document.getElementById("chatbox");
      if (!chatbox) return;

      chatbox.innerHTML = "";
      data.messages.forEach((msg) => {
        if (msg.role === "user") {
          appendMessage("You", msg.content);
        } else if (msg.role === "assistant") {
          appendMessage("AI", msg.content, msg.model_deployment_name, msg.message_id);
        } else if (msg.role === "file") {
          appendMessage("File", msg);
        } else if (msg.role === "image") {
          appendMessage("image", msg.content, msg.model_deployment_name);
        } else if (msg.role === "safety") {
          appendMessage("safety", msg.content);
        }
      });
    })
    .catch((error) => {
      console.error("Error loading messages:", error);
      showToast(`Error loading messages: ${error.message}`, "danger");
    });
}

/*************************************************
 *  CITATION PARSING
 *************************************************/
function parseCitations(message) {
  const citationRegex = /\(Source:\s*([^,]+),\s*Page(?:s)?:\s*([^)]+)\)\s*((?:\[#\S+?\]\s*)+)/g;
  return message.replace(citationRegex, (whole, filename, pages, bracketSection) => {
    let filenameHtml;
    if (/^https?:\/\/.+/i.test(filename.trim())) {
      filenameHtml = `<a href="${filename.trim()}" target="_blank" rel="noopener noreferrer">${filename.trim()}</a>`;
    } else {
      filenameHtml = filename.trim();
    }

    const idMatches = bracketSection.match(/\[#([^\]]+)\]/g);
    if (!idMatches) {
      return `(Source: ${filenameHtml}, Pages: ${pages})`;
    }

    const citationLinks = idMatches
      .map((m) => {
        const rawId = m.slice(2, -1);
        const pageNumber = rawId.split("_").pop();
        return `
          <a href="#"
             class="citation-link"
             data-citation-id="${rawId}"
             target="_blank"
             rel="noopener noreferrer"
          >[Page ${pageNumber}]</a>
        `;
      })
      .join(" ");

    return `(Source: ${filenameHtml}, Pages: ${pages}) ${citationLinks}`;
  });
}

/*************************************************
 *  DELETE A CONVERSATION
 *************************************************/
const conversationsList = document.getElementById("conversations-list");
if (conversationsList) {
  conversationsList.addEventListener("click", (event) => {
    const delBtn = event.target.closest(".delete-btn");
    if (delBtn) {
      event.stopPropagation();
      const conversationId = delBtn.getAttribute("data-conversation-id");
      deleteConversation(conversationId);
    } else {
      const convoItem = event.target.closest(".conversation-item");
      if (convoItem) {
        const conversationId = convoItem.getAttribute("data-conversation-id");
        selectConversation(conversationId);
      }
    }
  });
}

function deleteConversation(conversationId) {
  if (confirm("Are you sure you want to delete this conversation?")) {
    fetch(`/api/conversations/${conversationId}`, {
      method: "DELETE",
      headers: { "Content-Type": "application/json" },
    })
      .then((response) => {
        if (!response.ok) {
          return response.json().then(data => {
            throw new Error(data.error || `HTTP error ${response.status}`);
          });
        }
        return { success: true };
      })
      .then(() => {
        const convoItem = document.querySelector(
          `.conversation-item[data-conversation-id="${conversationId}"]`
        );
        if (convoItem) {
          convoItem.remove();
        }

        if (currentConversationId === conversationId) {
          currentConversationId = null;
          const titleEl = document.getElementById("current-conversation-title");
          if (titleEl) {
            titleEl.textContent =
              "Start typing to create a new conversation or select one on the left";
          }
          const chatbox = document.getElementById("chatbox");
          if (chatbox) {
            chatbox.innerHTML = "";
          }
        }
      })
      .catch((error) => {
        console.error("Error deleting conversation:", error);
        showToast(`Error deleting the conversation: ${error.message}`, "danger");
      });
  }
}

/*************************************************
 *  CITED TEXT FUNCTIONS
 *************************************************/
function fetchCitedText(citationId) {
  showLoadingIndicator();
  fetch("/api/get_citation", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ citation_id: citationId }),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then(data => {
          throw new Error(data.error || `HTTP error ${response.status}`);
        });
      }
      return response.json();
    })
    .then((data) => {
      hideLoadingIndicator();

      if (data.cited_text && data.file_name && data.page_number !== undefined) {
        showCitedTextPopup(data.cited_text, data.file_name, data.page_number);
      } else if (data.error) {
        showToast(data.error, "danger");
      } else {
        showToast("Unexpected response from server.", "danger");
      }
    })
    .catch((error) => {
      hideLoadingIndicator();
      console.error("Error fetching cited text:", error);
      showToast(`Error fetching cited text: ${error.message}`, "danger");
    });
}

function showCitedTextPopup(citedText, fileName, pageNumber) {
  let modalContainer = document.getElementById("citation-modal");
  if (!modalContainer) {
    modalContainer = document.createElement("div");
    modalContainer.id = "citation-modal";
    modalContainer.classList.add("modal", "fade");
    modalContainer.tabIndex = -1;
    modalContainer.setAttribute("aria-hidden", "true");

    modalContainer.innerHTML = `
      <div class="modal-dialog modal-dialog-scrollable modal-xl modal-fullscreen-sm-down">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Source: ${fileName}, Page: ${pageNumber}</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div id="cited-text-content" class="document-formatted"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modalContainer);
  } else {
    const modalTitle = modalContainer.querySelector(".modal-title");
    if (modalTitle) {
      modalTitle.textContent = `Source: ${fileName}, Page: ${pageNumber}`;
    }
  }

  const citedTextContent = document.getElementById("cited-text-content");
  if (citedTextContent) {
    // Format the text with improved paragraph detection
    citedTextContent.innerHTML = formatDocumentText(citedText);
  }

  const modal = new bootstrap.Modal(modalContainer);
  modal.show();
}

function formatDocumentText(text) {
  // Safety escape HTML characters
  let safeText = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
  
  // Split into lines
  const lines = safeText.split('\n');
  let formattedHtml = '';
  let inParagraph = false;
  
  lines.forEach((line, index) => {
    // Trim the line
    const trimmedLine = line.trim();
    
    // Skip empty lines
    if (trimmedLine === '') {
      if (inParagraph) {
        formattedHtml += '</p>\n';
        inParagraph = false;
      }
      return;
    }
    
    // Check if line is likely a heading
    const isHeading = /^(?:[A-Z\s0-9]+|[0-9]+\.\s+[A-Z])/.test(trimmedLine) && 
                      trimmedLine.length < 100 &&
                      !trimmedLine.includes(',');
    
    // Check if line is likely a new paragraph start
    const isNewParagraph = !inParagraph || 
                           /^(?:[A-Z*]|[0-9]+\.)/.test(trimmedLine) ||
                           (index > 0 && lines[index-1].trim() === '');
    
    if (isHeading) {
      // Close previous paragraph if needed
      if (inParagraph) {
        formattedHtml += '</p>\n';
        inParagraph = false;
      }
      
      // Add a heading with some spacing
      formattedHtml += `<h4 class="document-heading">${trimmedLine}</h4>\n`;
    } 
    else {
      // Regular paragraph content
      if (isNewParagraph) {
        // Close previous paragraph if needed
        if (inParagraph) {
          formattedHtml += '</p>\n';
        }
        
        // Start new paragraph
        formattedHtml += `<p class="document-paragraph">${trimmedLine}`;
        inParagraph = true;
      } 
      else {
        // Continue paragraph with space or line break
        formattedHtml += ` ${trimmedLine}`;
      }
    }
  });
  
  // Close final paragraph if needed
  if (inParagraph) {
    formattedHtml += '</p>\n';
  }
  
  return formattedHtml;
}

function enhanceParagraphBreaks(text) {
  // First, convert the text to HTML, preserving spaces and line breaks
  let htmlText = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>');
  
  // Look for paragraph breaks (double line breaks or more)
  // and enhance them with additional spacing for better readability
  htmlText = htmlText.replace(/(<br>)\s*(<br>)/g, '$1</p><p class="mt-3">');
  
  // Wrap the entire text in a paragraph
  htmlText = '<p>' + htmlText + '</p>';
  
  return htmlText;
}


function formatCitedText(text) {
  // Split text into paragraphs (empty lines as separators)
  const paragraphs = text.split(/\n\s*\n/);
  
  // Format each paragraph with proper styling
  const formattedParagraphs = paragraphs.map(p => {
    // Clean up the paragraph text (remove excessive whitespace)
    const cleanedText = p.trim().replace(/\s+/g, ' ');
    
    // Detect if the paragraph is a heading
    const isHeading = cleanedText.toUpperCase() === cleanedText && cleanedText.length < 100;
    
    if (isHeading) {
      return `<h5 class="mt-4 mb-2">${cleanedText}</h5>`;
    } else {
      return `<p class="mb-3">${cleanedText}</p>`;
    }
  });
  
  return formattedParagraphs.join('');
}


/*************************************************
 *  LOADING / HIDING INDICATORS
 *************************************************/
function showLoadingIndicator() {
  let loadingSpinner = document.getElementById("loading-spinner");
  if (!loadingSpinner) {
    loadingSpinner = document.createElement("div");
    loadingSpinner.id = "loading-spinner";
    loadingSpinner.innerHTML = `
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    `;
    loadingSpinner.style.position = "fixed";
    loadingSpinner.style.top = "50%";
    loadingSpinner.style.left = "50%";
    loadingSpinner.style.transform = "translate(-50%, -50%)";
    loadingSpinner.style.zIndex = "1050";
    document.body.appendChild(loadingSpinner);
  } else {
    loadingSpinner.style.display = "block";
  }
}

function hideLoadingIndicator() {
  const loadingSpinner = document.getElementById("loading-spinner");
  if (loadingSpinner) {
    loadingSpinner.style.display = "none";
  }
}

function showLoadingIndicatorInChatbox() {
  const chatbox = document.getElementById("chatbox");
  if (!chatbox) return;

  const loadingIndicator = document.createElement("div");
  loadingIndicator.classList.add("loading-indicator");
  loadingIndicator.id = "loading-indicator";
  loadingIndicator.innerHTML = `
    <div class="spinner-border text-primary" role="status">
      <span class="visually-hidden">AI is typing...</span>
    </div>
    <span>AI is typing...</span>
  `;
  chatbox.appendChild(loadingIndicator);
  chatbox.scrollTop = chatbox.scrollHeight;
}

function hideLoadingIndicatorInChatbox() {
  const loadingIndicator = document.getElementById("loading-indicator");
  if (loadingIndicator) {
    loadingIndicator.remove();
  }
}

/*************************************************
 *  CREATE A NEW CONVERSATION
 *************************************************/
async function createNewConversation(callback) {
  try {
    const response = await fetch("/api/create_conversation", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin"
    });
    
    if (!response.ok) {
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        const errData = await response.json();
        throw new Error(errData.error || `HTTP error ${response.status}`);
      } else {
        throw new Error(`HTTP error ${response.status}`);
      }
    }

    const data = await response.json();
    if (!data.conversation_id) {
      throw new Error("No conversation_id returned from server.");
    }

    currentConversationId = data.conversation_id;
    addConversationToList(data.conversation_id);

    const currentTitleEl = document.getElementById("current-conversation-title");
    if (currentTitleEl) {
      currentTitleEl.textContent = data.conversation_id;
    }

    const chatbox = document.getElementById("chatbox");
    if (chatbox) {
      chatbox.innerHTML = "";
    }

    if (typeof callback === "function") {
      callback();
    } else {
      loadMessages(data.conversation_id);
    }
  }  catch (error) {
    console.error("Error creating conversation:", error);
    showToast(`Failed to create a new conversation: ${error.message}`, "danger");
  }
}

/*************************************************
 *  SENDING A MESSAGE
 *************************************************/
function sendMessage() {
  const userInput = document.getElementById("user-input");
  
  // If the prompt dropdown is visible, use that value;
  // otherwise, use the typed input
  let textVal = "";
  if (promptSelect && promptSelect.style.display !== "none") {
    // They are in "prompt mode"
    const selectedOpt = promptSelect.options[promptSelect.selectedIndex];
    textVal = selectedOpt?.dataset?.promptContent?.trim() || "";
  } else if (userInput) {
    // They are in "typed input mode"
    textVal = userInput.value.trim();
  }

  if (!textVal) return;

  if (!currentConversationId) {
    // If no conversation, create one first, then send
    createNewConversation(() => {
      actuallySendMessage(textVal);
    });
  } else {
    actuallySendMessage(textVal);
  }
}

function actuallySendMessage(textVal) {
  const userInput = document.getElementById("user-input");
  appendMessage("You", textVal);
  userInput.value = "";
  
  // Get settings for the request
  let hybridSearchEnabled = false;
  const sdbtn = document.getElementById("search-documents-btn");
  if (sdbtn && sdbtn.classList.contains("active")) {
    hybridSearchEnabled = true;
  }

  let selectedDocumentId = null;
  if (hybridSearchEnabled) {
    const docSel = document.getElementById("document-select");
    if (docSel && docSel.value !== "" && docSel.value !== "All Documents") {
      selectedDocumentId = docSel.value;
    }
  }

  let bingSearchEnabled = false;
  const wbbtn = document.getElementById("search-web-btn");
  if (wbbtn && wbbtn.classList.contains("active")) {
    bingSearchEnabled = true;
  }

  let imageGenEnabled = false;
  const igbtn = document.getElementById("image-generate-btn");
  if (igbtn && igbtn.classList.contains("active")) {
    imageGenEnabled = true;
  }
  
  // Get docScopeSelect value safely
  const docScopeValue = docScopeSelect ? docScopeSelect.value : null;
  
  // Create payload with streaming enabled
  const payload = {
    message: textVal,
    conversation_id: currentConversationId,
    hybrid_search: hybridSearchEnabled,
    selected_document_id: selectedDocumentId,
    bing_search: bingSearchEnabled,
    image_generation: imageGenEnabled,
    doc_scope: docScopeValue,
    active_group_id: activeGroupId || null,
    streaming: true // Enable streaming by default
  };

  // Create empty message element for streaming content
  const messageDiv = document.createElement("div");
  messageDiv.classList.add("mb-2", "message", "ai-message");
  messageDiv.innerHTML = `
    <div class="message-content">
      <img src="/static/images/ai-avatar.png" alt="AI Avatar" class="avatar">
      <div class="message-bubble">
        <div class="message-sender">AI <span style="color: #6c757d; font-size: 0.8em;">(streaming)</span></div>
        <div class="message-text"></div>
      </div>
    </div>
  `;
  
  // Add the message to the chatbox
  const chatbox = document.getElementById("chatbox");
  if (chatbox) {
    chatbox.appendChild(messageDiv);
    scrollChatToBottom();
  }
  
  const messageTextElement = messageDiv.querySelector(".message-text");
  const messageSenderElement = messageDiv.querySelector(".message-sender");
  let fullContent = "";
  let conversationId = currentConversationId;
  let messageId = null;
  let modelName = null;

  fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then(response => {
      if (!response.ok) {
        // Handle error response
        return response.json().then(data => {
          return {
            ok: false,
            status: response.status,
            data
          };
        }).catch(() => {
          // If JSON parsing fails, return a generic error
          return {
            ok: false,
            status: response.status,
            data: { error: `HTTP error ${response.status}` }
          };
        });
      }
      
      // Check if the response is a streaming response
      const contentType = response.headers.get("Content-Type") || "";
      
      if (contentType.includes("text/event-stream")) {
        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        // Process the stream
        function processStream() {
          return reader.read().then(({ done, value }) => {
            if (done) {
              // Stream has ended
              if (messageTextElement) {
                // Apply citation parsing to the final content
                let cleaned = fullContent.trim().replace(/\n{3,}/g, "\n\n");
                cleaned = cleaned.replace(/(\bhttps?:\/\/\S+)(%5D|\])+/gi, (_, url) => url);
                const withCitations = parseCitations(cleaned);
                
                // Update with final formatted content
                messageTextElement.innerHTML = DOMPurify.sanitize(marked.parse(withCitations));
                
                // Add feedback icons
                if (messageId) {
                  const feedbackHtml = renderFeedbackIcons(messageId, conversationId);
                  const messageBubble = messageDiv.querySelector(".message-bubble");
                  if (messageBubble && feedbackHtml) {
                    const feedbackContainer = document.createElement('div');
                    feedbackContainer.innerHTML = feedbackHtml;
                    messageBubble.appendChild(feedbackContainer.firstChild);
                  }
                }

                // Update the AI label with model name if available
                if (modelName && messageSenderElement) {
                  messageSenderElement.innerHTML = `AI <span style="color: #6c757d; font-size: 0.8em;">(${modelName})</span>`;
                }
              }
              return;
            }
            
            // Decode the chunk and add to buffer
            buffer += decoder.decode(value, { stream: true });
            
            // Process complete lines in the buffer
            const lines = buffer.split('\n\n');
            buffer = lines.pop() || '';  // Keep the last incomplete line in buffer
            
            for (const line of lines) {
              if (line.trim() === '') continue;
              
              if (line.startsWith('data: ')) {
                try {
                  // Extract JSON payload by removing 'data: ' prefix
                  const jsonStr = line.substring(6);
                  const data = JSON.parse(jsonStr);
                  
                  // Handle different types of messages
                  if (data.type === 'info') {
                    // Store conversation and message IDs
                    conversationId = data.conversation_id || conversationId;
                    messageId = data.message_id || null;
                    
                    if (data.conversation_title) {
                      const convTitleEl = document.getElementById("current-conversation-title");
                      if (convTitleEl) {
                        convTitleEl.textContent = data.conversation_title;
                      }
                      
                      // Update the conversation in the list if it exists
                      updateConversationInList(conversationId, data.conversation_title);
                    }
                  } 
                  else if (data.type === 'chunk') {
                    // Append content to the message
                    if (messageTextElement && data.content) {
                      fullContent += data.content;
                      // Convert to markdown for display
                      messageTextElement.innerHTML = DOMPurify.sanitize(marked.parse(fullContent));
                      scrollChatToBottom();
                    }
                  } 
                  else if (data.type === 'done') {
                    // Streaming complete
                    modelName = data.model_deployment_name || null;
                  } 
                  else if (data.type === 'error') {
                    // Handle error
                    if (messageTextElement) {
                      messageTextElement.innerHTML = `<div class="error-message">Error: ${data.error}</div>`;
                    }
                  }
                } catch (e) {
                  console.error('Error parsing SSE data:', e, line);
                }
              }
            }
            
            // Continue reading the stream
            return processStream();
          }).catch(error => {
            console.error("Stream reading error:", error);
            if (messageTextElement) {
              messageTextElement.innerHTML += `<div class="error-message">Error: Stream interrupted</div>`;
            }
          });
        }
        
        return { isStream: true, processStream: processStream() };
      } else {
        // Not a streaming response, handle as regular JSON
        return { isStream: false, json: response.json() };
      }
    })
    .then(result => {
      if (result.isStream) {
        // The stream is already being processed
        return;
      } else {
        // Handle regular JSON response (fallback for non-streaming)
        return result.json.then(data => {
          // Remove the empty streaming message element
          if (messageDiv && messageDiv.parentNode) {
            messageDiv.parentNode.removeChild(messageDiv);
          }
          
          if (data.ok === false) {
            if (data.status === 403) {
              const categories = (data.data.triggered_categories || [])
                .map((catObj) => `${catObj.category} (severity=${catObj.severity})`)
                .join(", ");
              const reasonMsg = Array.isArray(data.data.reason)
                ? data.data.reason.join(", ")
                : data.data.reason || "Unknown reason";
    
              appendMessage(
                "System",
                `Your message was blocked by Content Safety.\n\n` +
                  `**Categories triggered**: ${categories}\n` +
                  `**Reason**: ${reasonMsg}`
              );
            } else {
              appendMessage(
                "System",
                `An error occurred: ${data.data.error || "Unknown error"}.`
              );
            }
          } else {
            if (data.reply) {
              appendMessage("AI", data.reply, data.model_deployment_name, data.message_id);
            }
            
            if (data.image_url) {
              appendMessage("image", data.image_url, data.model_deployment_name, data.message_id);
            }
            
            if (data.conversation_id) {
              currentConversationId = data.conversation_id;
            }
            
            if (data.conversation_title) {
              const convTitleEl = document.getElementById("current-conversation-title");
              if (convTitleEl) {
                convTitleEl.textContent = data.conversation_title;
              }
              
              updateConversationInList(data.conversation_id, data.conversation_title);
            }
          }
        });
      }
    })
    .catch(error => {
      console.error("Error:", error);
      
      // Remove the streaming message if it exists
      if (messageDiv && messageDiv.parentNode) {
        messageDiv.parentNode.removeChild(messageDiv);
      }
      
      appendMessage("Error", "Could not get a response. Please try again.");
    });
}

/*************************************************
 *  USER INPUT EVENT LISTENERS
 *************************************************/
const sendBtn = document.getElementById("send-btn");
if (sendBtn) {
  sendBtn.addEventListener("click", sendMessage);
}

// userInput is already defined at the top
if (userInput) {
  userInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter") {
      sendMessage();
    }
  });
}

/*************************************************
 *  FILE UPLOAD LOGIC
 *************************************************/
const chooseFileBtn = document.getElementById("choose-file-btn");
if (chooseFileBtn) {
  chooseFileBtn.addEventListener("click", function () {
    const fileInput = document.getElementById("file-input");
    if (fileInput) fileInput.click();
  });
}

const fileInputEl = document.getElementById("file-input");
if (fileInputEl) {
  fileInputEl.addEventListener("change", function () {
    const file = fileInputEl.files[0];
    const fileBtn = document.getElementById("choose-file-btn");
    const uploadBtn = document.getElementById("upload-btn");
    if (!fileBtn || !uploadBtn) return;

    if (file) {
      fileBtn.classList.add("active");
      const fileBtnText = fileBtn.querySelector(".file-btn-text");
      if (fileBtnText) {
        fileBtnText.textContent = file.name;
      }
      uploadBtn.style.display = "block";
    } else {
      resetFileButton();
    }
  });
}

function resetFileButton() {
  const fileInputEl = document.getElementById("file-input");
  if (fileInputEl) {
    fileInputEl.value = "";
  }
  const fileBtn = document.getElementById("choose-file-btn");
  if (fileBtn) {
    fileBtn.classList.remove("active");
    const fileBtnText = fileBtn.querySelector(".file-btn-text");
    if (fileBtnText) {
      fileBtnText.textContent = "";
    }
  }
  const uploadBtn = document.getElementById("upload-btn");
  if (uploadBtn) {
    uploadBtn.style.display = "none";
  }
}

const uploadBtn = document.getElementById("upload-btn");
if (uploadBtn) {
  uploadBtn.addEventListener("click", () => {
    const fileInput = document.getElementById("file-input");
    if (!fileInput) return;

    const file = fileInput.files[0];
    if (!file) {
      showToast("Please select a file to upload.", "danger");
      return;
    }

    if (!currentConversationId) {
      createNewConversation(() => {
        uploadFileToConversation(file);
      });
    } else {
      uploadFileToConversation(file);
    }
  });
}

function uploadFileToConversation(file) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("conversation_id", currentConversationId);

  fetch("/upload", {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then(data => {
          console.error("Upload failed:", data.error || "Unknown error");
          showToast("Error uploading file: " + (data.error || "Unknown error"), "danger");
          throw new Error(data.error || "Upload failed");
        }).catch(error => {
          if (error instanceof SyntaxError) {
            // JSON parsing error
            console.error("Upload failed: Invalid server response");
            showToast("Error uploading file: Invalid server response", "danger");
            throw new Error("Invalid server response");
          }
          throw error;
        });
      }
      return response.json();
    })
    .then((data) => {
      if (data.conversation_id) {
        currentConversationId = data.conversation_id;
        loadMessages(currentConversationId);
      } else {
        console.error("No conversation_id returned from server.");
        showToast("Error: No conversation ID returned from server.", "danger");
      }
      resetFileButton();
    })
    .catch((error) => {
      console.error("Error:", error);
      showToast("Error uploading file: " + error.message, "danger");
      resetFileButton();
    });
}

/*************************************************
 *  CITATION LINKS & FILE LINKS
 *************************************************/
const chatboxEl = document.getElementById("chatbox");
if (chatboxEl) {
  chatboxEl.addEventListener("click", (event) => {
    if (event.target && event.target.matches("a.citation-link")) {
      event.preventDefault();
      const citationId = event.target.getAttribute("data-citation-id");
      fetchCitedText(citationId);
    } else if (event.target && event.target.matches("a.file-link")) {
      event.preventDefault();
      const fileId = event.target.getAttribute("data-file-id");
      const conversationId = event.target.getAttribute("data-conversation-id");
      fetchFileContent(conversationId, fileId);
    }
    if (event.target.classList.contains("generated-image")) {
      const imageSrc = event.target.getAttribute("data-image-src");
      showImagePopup(imageSrc);
    }
  });
}

function showImagePopup(imageSrc) {
  let modalContainer = document.getElementById("image-modal");
  if (!modalContainer) {
    modalContainer = document.createElement("div");
    modalContainer.id = "image-modal";
    modalContainer.classList.add("modal", "fade");
    modalContainer.tabIndex = -1;
    modalContainer.setAttribute("aria-hidden", "true");

    modalContainer.innerHTML = `
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
          <div class="modal-body text-center">
            <img
              id="image-modal-img"
              src=""
              alt="Generated Image"
              class="img-fluid"
            />
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modalContainer);
  }
  const modalImage = modalContainer.querySelector("#image-modal-img");
  if (modalImage) {
    modalImage.src = imageSrc;
  }
  const modal = new bootstrap.Modal(modalContainer);
  modal.show();
}

function fetchFileContent(conversationId, fileId) {
  showLoadingIndicator();
  fetch("/api/get_file_content", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      conversation_id: conversationId,
      file_id: fileId,
    }),
  })
    .then((response) => {
      if (!response.ok) {
        return response.json().then(data => {
          throw new Error(data.error || `HTTP error ${response.status}`);
        }).catch(error => {
          if (error instanceof SyntaxError) {
            throw new Error(`HTTP error ${response.status}`);
          }
          throw error;
        });
      }
      return response.json();
    })
    .then((data) => {
      hideLoadingIndicator();

      if (data.file_content && data.filename) {
        showFileContentPopup(data.file_content, data.filename, data.is_table);
      } else if (data.error) {
        showToast(data.error, "danger");
      } else {
        showToast("Unexpected response from server.", "danger");
      }
    })
    .catch((error) => {
      hideLoadingIndicator();
      console.error("Error fetching file content:", error);
      showToast(`Error fetching file content: ${error.message}`, "danger");
    });
}

function showFileContentPopup(fileContent, filename, isTable) {
  let modalContainer = document.getElementById("file-modal");
  if (!modalContainer) {
    modalContainer = document.createElement("div");
    modalContainer.id = "file-modal";
    modalContainer.classList.add("modal", "fade");
    modalContainer.tabIndex = -1;
    modalContainer.setAttribute("aria-hidden", "true");

    modalContainer.innerHTML = `
      <div class="modal-dialog modal-dialog-scrollable modal-xl modal-fullscreen-sm-down">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title">Uploaded File: ${filename}</h5>
            <button
              type="button"
              class="btn-close"
              data-bs-dismiss="modal"
              aria-label="Close"
            ></button>
          </div>
          <div class="modal-body">
            <div id="file-content"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modalContainer);
  } else {
    const modalTitle = modalContainer.querySelector(".modal-title");
    if (modalTitle) {
      modalTitle.textContent = `Uploaded File: ${filename}`;
    }
  }

  const fileContentElement = document.getElementById("file-content");
  if (!fileContentElement) return;

  if (isTable) {
    fileContentElement.innerHTML = `<div class="table-responsive">${fileContent}</div>`;
    $(document).ready(function () {
      $("#file-content table").DataTable({
        responsive: true,
        scrollX: true,
      });
    });
  } else {
    fileContentElement.innerHTML = `<pre style="white-space: pre-wrap;">${fileContent}</pre>`;
  }

  const modal = new bootstrap.Modal(modalContainer);
  modal.show();
}

/*************************************************
 *  BOOTSTRAP TOOLTIPS
 *************************************************/
document.addEventListener("DOMContentLoaded", function () {
  const tooltipTriggerList = [].slice.call(
    document.querySelectorAll('[data-bs-toggle="tooltip"]')
  );
  tooltipTriggerList.forEach(function (tooltipTriggerEl) {
    new bootstrap.Tooltip(tooltipTriggerEl);
  });
});

/*************************************************
 *  ON PAGE LOAD
 *************************************************/
window.onload = function () {
  loadConversations();

  // Use Promise.all to run these in parallel.
  Promise.all([
    loadAllDocs(),       // loads personal/group docs
    loadUserPrompts(),   // loads user prompts
    loadGroupPrompts()   // loads group prompts
  ])
    .then(() => {
      // Auto-enable document search by default
      const searchDocsBtn = document.getElementById("search-documents-btn");
      const docScopeSel = document.getElementById("doc-scope-select");
      const docSelectEl = document.getElementById("document-select");

      if (searchDocsBtn && docScopeSel && docSelectEl) {
        // Simulate clicking the search documents button
        searchDocsBtn.classList.add("active");
        docScopeSel.style.display = "inline-block";
        docSelectEl.style.display = "inline-block";
        populateDocumentSelectScope();
      }

      // Continue handling URL params if needed
      const searchDocsParam = getUrlParameter("search_documents") === "true";
      const docScopeParam = getUrlParameter("doc_scope") || "";
      const documentIdParam = getUrlParameter("document_id") || "";

      if (searchDocsParam && docScopeParam) {
        if (docScopeSel) docScopeSel.value = docScopeParam;
        populateDocumentSelectScope();

        if (documentIdParam && docSelectEl) {
          docSelectEl.value = documentIdParam;
        }
      }
    })
    .catch((err) => {
      console.error("Error loading initial data:", err);
    });
};

const newConversationBtn = document.getElementById("new-conversation-btn");
if (newConversationBtn) {
  newConversationBtn.addEventListener("click", () => {
    createNewConversation();
  });
}

/*************************************************
 *  OPTIONAL: GET URL PARAM
 *************************************************/
function getUrlParameter(name) {
  name = name.replace(/[\[]/, "\\[").replace(/[\]]/, "\\]");
  const regex = new RegExp("[\\?&]" + name + "=([^&#]*)");
  const results = regex.exec(location.search);
  return results === null
    ? ""
    : decodeURIComponent(results[1].replace(/\+/g, " "));
}

function toBoolean(str) {
  return String(str).toLowerCase() === "true";
}

/*************************************************
 *  THUMBS UP / DOWN FEEDBACK
 *************************************************/
function renderFeedbackIcons(messageId, conversationId) {
  
  if (window.enableUserFeedback && toBoolean(window.enableUserFeedback)) {
    return `
      <div class="feedback-icons" data-ai-message-id="${messageId}">
        <i class="bi bi-hand-thumbs-up-fill text-muted me-3 feedback-btn" 
          data-feedback-type="positive" 
          data-conversation-id="${conversationId}"
          title="Thumbs Up"
          style="cursor:pointer;"></i>
        <i class="bi bi-hand-thumbs-down-fill text-muted feedback-btn" 
          data-feedback-type="negative" 
          data-conversation-id="${conversationId}"
          title="Thumbs Down"
          style="cursor:pointer;"></i>
      </div>
    `;
  }
  else {
    return "";
  }
}

// Add event listener for thumbs up/down
document.addEventListener("click", function (event) {
  const feedbackBtn = event.target.closest(".feedback-btn");
  if (!feedbackBtn) return;

  const feedbackType = feedbackBtn.getAttribute("data-feedback-type");
  const feedbackIcons = feedbackBtn.closest(".feedback-icons");
  
  if (!feedbackIcons) {
    console.error("Could not find parent .feedback-icons element");
    return;
  }
  
  const messageId = feedbackIcons.getAttribute("data-ai-message-id");
  const conversationId = feedbackBtn.getAttribute("data-conversation-id");

  if (!messageId || !conversationId) {
    console.error("Missing required attributes:", { messageId, conversationId });
    return;
  }

  // 1) VISUAL FEEDBACK: Add "clicked" class
  feedbackBtn.classList.add("clicked");

  if (feedbackType === "positive") {
    // Immediately submit thumbs-up, no reason needed
    submitFeedback(messageId, conversationId, "positive", "");

    // 2) Remove the class after 500ms or so
    setTimeout(() => {
      feedbackBtn.classList.remove("clicked");
    }, 500);
  } else {
    // Thumbs down => open modal for optional reason
    const feedbackModal = document.getElementById("feedback-modal");
    if (!feedbackModal) {
      console.error("Feedback modal not found");
      return;
    }
    
    const modalEl = new bootstrap.Modal(feedbackModal);
    
    const messageIdInput = document.getElementById("feedback-ai-response-id");
    const conversationIdInput = document.getElementById("feedback-conversation-id");
    const feedbackTypeInput = document.getElementById("feedback-type");
    const reasonInput = document.getElementById("feedback-reason");
    
    if (messageIdInput) messageIdInput.value = messageId;
    if (conversationIdInput) conversationIdInput.value = conversationId;
    if (feedbackTypeInput) feedbackTypeInput.value = "negative";
    if (reasonInput) reasonInput.value = "";
    
    modalEl.show();
  }
});

// Form submission for thumbs-down reason
const feedbackForm = document.getElementById("feedback-form");
if (feedbackForm) {
  feedbackForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const messageId = document.getElementById("feedback-ai-response-id")?.value;
    const conversationId = document.getElementById("feedback-conversation-id")?.value;
    const feedbackType = document.getElementById("feedback-type")?.value;
    const reason = document.getElementById("feedback-reason")?.value?.trim() || "";

    if (!messageId || !conversationId || !feedbackType) {
      console.error("Missing required feedback fields");
      return;
    }

    // Submit feedback
    submitFeedback(messageId, conversationId, feedbackType, reason);

    // Hide modal
    const feedbackModal = document.getElementById("feedback-modal");
    if (feedbackModal) {
      const modalEl = bootstrap.Modal.getInstance(feedbackModal);
      if (modalEl) modalEl.hide();
    }
  });
}

function submitFeedback(messageId, conversationId, feedbackType, reason) {
  fetch("/feedback/submit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messageId,
      conversationId,
      feedbackType,
      reason
    }),
  })
    .then((resp) => {
      if (!resp.ok) {
        return resp.json().then(data => {
          throw new Error(data.error || `HTTP error ${resp.status}`);
        }).catch(error => {
          if (error instanceof SyntaxError) {
            throw new Error(`HTTP error ${resp.status}`);
          }
          throw error;
        });
      }
      return resp.json();
    })
    .then((data) => {
      if (data.success) {
        // Optionally highlight the icons or show a "thank you" message
        console.log("Feedback submitted:", data);
      } else {
        throw new Error(data.error || "Unknown error");
      }
    })
    .catch((err) => {
      console.error("Error sending feedback:", err);
      showToast(`Error sending feedback: ${err.message}`, "danger");
    });
}

function showToast(message, variant = "danger") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const id = "toast-" + Date.now();
  const toastHtml = `
    <div id="${id}" class="toast align-items-center text-bg-${variant}" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body">
          ${message}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;
  container.insertAdjacentHTML("beforeend", toastHtml);

  const toastEl = document.getElementById(id);
  if (toastEl) {
    const bsToast = new bootstrap.Toast(toastEl, { delay: 5000 });
    bsToast.show();
  }
}