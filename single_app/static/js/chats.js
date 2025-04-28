// Application state
let personalDocs = [];
let groupDocs = [];
let activeGroupName = "";
let currentConversationId = null;
let userPrompts = [];
let groupPrompts = [];
let activeGroupId = null; // Define activeGroupId variable
// Add these variables to the top of the file with other application state variables
let userGroups = [];
let selectedGroupId = null;

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
// Update this function in chats.js
function populateDocumentSelectScope() {
  console.group("📄 Populating Document Select");
  
  const scopeSel = document.getElementById("doc-scope-select");
  const docSel = document.getElementById("document-select");
  if (!scopeSel || !docSel) {
    console.warn("Cannot find document scope or document select elements");
    console.groupEnd();
    return;
  }

  docSel.innerHTML = "";
  console.log("Cleared document select options");

  // Add "All Documents" option
  const noneOpt = document.createElement("option");
  noneOpt.value = "";
  noneOpt.textContent = "All Documents";
  docSel.appendChild(noneOpt);

  const scopeVal = scopeSel.value || "all";
  console.log("Current scope value:", scopeVal);
  console.log("Personal docs available:", personalDocs.length);
  console.log("Group docs available:", groupDocs.length);
  
  // Create personal documents section
  if ((scopeVal === "all" || scopeVal === "personal") && personalDocs.length > 0) {
    const personalOptgroup = document.createElement("optgroup");
    personalOptgroup.label = "Personal Documents";
    
    // Deduplicate personal docs by file name
    const uniquePersonalDocs = {};
    personalDocs.forEach(doc => {
      if (!doc.file_name) return;
      
      // Keep the document with the highest version or most recent upload_date
      if (!uniquePersonalDocs[doc.file_name] || 
          (doc.version && uniquePersonalDocs[doc.file_name].version && 
           doc.version > uniquePersonalDocs[doc.file_name].version)) {
        uniquePersonalDocs[doc.file_name] = doc;
      }
    });
    
    // Add unique personal documents to the optgroup
    Object.values(uniquePersonalDocs).forEach(doc => {
      const opt = document.createElement("option");
      opt.value = doc.id;
      opt.textContent = doc.file_name;
      opt.dataset.isGroup = "false";
      personalOptgroup.appendChild(opt);
    });
    
    docSel.appendChild(personalOptgroup);
  }
  
  // Create group documents sections - organized by group name
  if ((scopeVal === "all" || scopeVal === "group") && groupDocs.length > 0) {
    // Group documents by group name
    const groupsByName = {};
    
    groupDocs.forEach(doc => {
      if (!doc.file_name) return;
      
      const groupName = doc.group_name || "Unknown Group";
      const groupId = doc.group_id || "";
      
      if (!groupsByName[groupName]) {
        groupsByName[groupName] = {
          groupId: groupId,
          docs: {},  // Changed to object for deduplication
          docsList: []  // Will store final deduplicated docs
        };
      }
      
      // Store by filename to deduplicate
      const fileName = doc.file_name;
      const currentGroup = groupsByName[groupName];
      
      // Only add if filename doesn't exist or this version is newer
      if (!currentGroup.docs[fileName] || 
          (doc.version && currentGroup.docs[fileName].version && 
           doc.version > currentGroup.docs[fileName].version)) {
        currentGroup.docs[fileName] = doc;
      }
    });
    
    // Convert deduplicated docs object back to array for each group
    Object.values(groupsByName).forEach(group => {
      group.docsList = Object.values(group.docs);
    });
    
    // Add each group's documents
    Object.entries(groupsByName).forEach(([groupName, group]) => {
      const groupOptgroup = document.createElement("optgroup");
      groupOptgroup.label = `Group: ${groupName}`;
      
      // Only add each unique document once
      group.docsList.forEach(doc => {
        const opt = document.createElement("option");
        opt.value = doc.id;
        opt.textContent = doc.file_name;
        opt.dataset.isGroup = "true";
        opt.dataset.groupId = doc.group_id;
        opt.dataset.groupName = groupName;
        groupOptgroup.appendChild(opt);
      });
      
      if (groupOptgroup.children.length > 0) {
        docSel.appendChild(groupOptgroup);
      }
    });
  }
  
  console.log("Populated document select dropdown with organized categories");
  console.groupEnd();
}
 

// Update the document scope select to include "all groups" option
function setupDocumentScopeSelect() {
  const docScopeSelect = document.getElementById("doc-scope-select");
  if (!docScopeSelect) return;
  
  // Clear existing options
  docScopeSelect.innerHTML = "";
  
  // Add options
  const options = [
    { value: "all", label: "All Documents" },
    { value: "personal", label: "My Documents" },
    { value: "group", label: "All My Groups" }
  ];
  
  options.forEach(option => {
    const opt = document.createElement("option");
    opt.value = option.value;
    opt.textContent = option.label;
    docScopeSelect.appendChild(opt);
  });
  
  // Add event listener for scope changes
  docScopeSelect.addEventListener("change", function() {
    populateDocumentSelectScope();
  });
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
  console.log("Loading documents from user's groups");
  
  // First get active group info for UI purposes
  return fetch("/api/groups")
    .then((response) => {
      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }
      return response.json();
    })
    .then((groups) => {
      // Store active group info for the UI
      const activeGroup = groups.find((g) => g.isActive);
      if (activeGroup) {
        activeGroupName = activeGroup.name || "Active Group";
        activeGroupId = activeGroup.id || null;
        console.log(`Active group: ${activeGroupName} (${activeGroupId})`);
      } else {
        activeGroupName = "";
        activeGroupId = null;
      }
      
      // Get documents from user's groups
      return fetch("/api/all_group_documents")
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
          
          // Store group documents
          groupDocs = data.documents || [];
          console.log(`Loaded ${groupDocs.length} documents from user's groups`);
          
          // Log the groups we found documents from
          if (groupDocs.length > 0) {
            const groupNames = [...new Set(groupDocs.map(doc => doc.group_name))];
            console.log("Documents found from these groups:", groupNames);
          } else {
            console.warn("No group documents found");
          }
        })
        .catch((err) => {
          console.error("Error loading group docs:", err);
          groupDocs = [];
        });
    })
    .catch((err) => {
      console.error("Error loading groups:", err);
      activeGroupName = "";
      activeGroupId = null;
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

  // Wrap both calls in Promise.resolve to ensure they're always Promises
  return Promise.resolve(loadPersonalDocs())
    .then(() => Promise.resolve(loadGroupDocs()))
    .catch(err => {
      console.error("Error in loadAllDocs:", err);
      return Promise.resolve(); // Ensure the chain continues
    });
}

/*************************************************
 *  TOGGLE BUTTONS: SEARCH DOCUMENTS, WEB SEARCH, IMAGE GEN
 *************************************************/
const searchDocumentsBtn = document.getElementById("search-documents-btn");
if (searchDocumentsBtn) {
  // Save the original event listener
  const originalClickHandler = searchDocumentsBtn.onclick;
  
  // Replace with enhanced version
  searchDocumentsBtn.addEventListener("click", function () {
    console.group("🔎 Document Search Button Toggle");
    
    const wasActive = this.classList.contains("active");
    console.log("Was active before click:", wasActive);
    
    // Toggle active state
    this.classList.toggle("active");
    const isNowActive = this.classList.contains("active");
    console.log("Is active after click:", isNowActive);

    const docScopeSel = document.getElementById("doc-scope-select");
    const docSelectEl = document.getElementById("document-select");
    if (!docScopeSel || !docSelectEl) {
      console.warn("Document scope or select elements not found");
      console.groupEnd();
      return;
    }

    if (isNowActive) {
      console.log("Enabling document selection UI");
      docScopeSel.style.display = "inline-block";
      docSelectEl.style.display = "inline-block";
      
      // Load personal and group documents if needed
      console.log("Loading documents...");
      const personalLoaded = personalDocs.length > 0;
      const groupLoaded = groupDocs.length > 0;
      
      console.log("Personal docs already loaded:", personalLoaded, "count:", personalDocs.length);
      console.log("Group docs already loaded:", groupLoaded, "count:", groupDocs.length);
      
      if (!personalLoaded || !groupLoaded) {
        console.log("Need to load documents, calling loadAllDocs()");
        loadAllDocs().then(() => {
          console.log("Documents loaded, populating document select");
          populateDocumentSelectScope();
        });
      } else {
        console.log("Documents already loaded, populating document select");
        populateDocumentSelectScope();
      }
    } else {
      console.log("Disabling document selection UI");
      docScopeSel.style.display = "none";
      docSelectEl.style.display = "none";
      docSelectEl.innerHTML = "";
    }
    
    console.groupEnd();
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
// Updated fetchCitedText function to handle page numbers correctly
// Update the fetchCitedText function to use the new universal document viewer
function fetchCitedText(citationId) {
  console.log('Fetching citation for ID:', citationId);
  showLoadingIndicator();
  
  var xhr = new XMLHttpRequest();
  xhr.open("POST", "/api/get_citation", true);
  xhr.setRequestHeader("Content-Type", "application/json");
  xhr.onreadystatechange = function() {
    if (xhr.readyState === 4) {
      hideLoadingIndicator();
      
      if (xhr.status === 200) {
        try {
          var data = JSON.parse(xhr.responseText);
          console.log("Citation data received:", data);
          
          // Use the new document_viewer_url if available, or fall back to regular PDF viewer
          if (data.document_viewer_url) {
            showDocumentInUniversalViewer(data);
          } 
          else if (data.document_url) {
            var pageNumber = 1;
            if (data.document_source && typeof data.document_source.page !== 'undefined') {
              pageNumber = data.document_source.page;
            }
            
            var documentName = "Document";
            if (data.document_source && data.document_source.name) {
              documentName = data.document_source.name;
            }
            
            // Use old PDF viewer as fallback
            showDocumentInIframe(data.document_url, documentName, pageNumber);
          } 
          else if (data.cited_text) {
            var sourceName = "Unknown Document";
            var sourcePage = 1;
            
            if (data.document_source) {
              if (data.document_source.name) {
                sourceName = data.document_source.name;
              }
              if (typeof data.document_source.page !== 'undefined') {
                sourcePage = data.document_source.page;
              }
            }
            
            showCitedTextPopup(data.cited_text, sourceName, sourcePage);
          } 
          else if (data.error) {
            showToast(data.error, 'danger');
          } 
          else {
            showToast("Unexpected response from server.", 'danger');
          }
        } catch (e) {
          console.error("Error parsing response:", e);
          showToast("Error parsing server response", "danger");
        }
      } else {
        console.error("Request failed with status:", xhr.status);
        showToast("Failed to fetch citation: HTTP " + xhr.status, "danger");
      }
    }
  };
  xhr.onerror = function() {
    hideLoadingIndicator();
    console.error("Network error during request");
    showToast("Network error while fetching citation", "danger");
  };
  xhr.send(JSON.stringify({ citation_id: citationId }));
}

// Add new function to show document in universal viewer
function showDocumentInUniversalViewer(data) {
  console.log("Using universal document viewer with data:", data);
  
  // Get or create the modal
  let modal = document.getElementById('citation-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'citation-modal';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = `
      <div class="modal-dialog modal-fullscreen">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body p-0">
            <div class="document-viewer-container" style="width: 100%; height: 90vh;"></div>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
  }
  
  // Set the modal title
  const docName = data.document_source?.name || "Document";
  const docPage = data.document_source?.page || 1;
  const fileType = data.document_source?.file_type || "";
  
  const modalTitle = modal.querySelector('.modal-title');
  if (modalTitle) {
    // Add file type info to the title
    let titleText = `Source: ${docName}, Page: ${docPage}`;
    if (fileType) {
      titleText += ` (${fileType.toUpperCase()})`;
    }
    modalTitle.textContent = titleText;
  }
  
  // Get the container
  const container = modal.querySelector('.document-viewer-container');
  if (!container) {
    console.error("Document viewer container not found");
    return;
  }
  
  // Clear any existing content
  container.innerHTML = '';
  
  // Add a loading indicator
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'spinner-border text-primary';
  loadingDiv.role = 'status';
  loadingDiv.style = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);';
  loadingDiv.innerHTML = '<span class="visually-hidden">Loading...</span>';
  container.appendChild(loadingDiv);
  
  // Create iframe to load the universal document viewer
  const iframe = document.createElement('iframe');
  iframe.src = data.document_viewer_url;
  iframe.style = 'width: 100%; height: 100%; border: none;';
  iframe.allow = 'fullscreen';
  iframe.id = 'document-viewer-iframe';
  
  // When iframe loads, remove the loading indicator
  iframe.onload = function() {
    if (loadingDiv && loadingDiv.parentNode) {
      loadingDiv.parentNode.removeChild(loadingDiv);
    }
  };
  
  // If iframe fails to load, show error
  iframe.onerror = function() {
    console.error("Error loading document viewer iframe");
    container.innerHTML = `
      <div class="alert alert-danger m-3">
        <h4>Error Loading Document</h4>
        <p>There was a problem loading the document. Please try again later.</p>
      </div>
    `;
  };
  
  // Add the iframe to the container
  container.appendChild(iframe);
  
  // Show the modal
  const bsModal = new bootstrap.Modal(modal);
  bsModal.show();
  
  // Update the event listener for messages from the iframe
  window.addEventListener('message', function(event) {
    // Process messages from the document viewer iframe
    if (event.data === 'close-document-modal' || event.data === 'close-pdf-modal') {
      const modal = document.getElementById('citation-modal');
      if (modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
          modalInstance.hide();
        }
      }
    }
  }, false);
}

// Update parseCitations function to handle additional file types
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

    // Extract the exact page number text without trying to parse/modify it
    const pageText = pages.trim();
    
    // Detect file type from extension
    let fileIcon = "📄"; // Default document icon
    const extension = filename.split('.').pop().toLowerCase();
    
    if (['pdf'].includes(extension)) {
      fileIcon = "📕"; // Book for PDF
    } else if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(extension)) {
      fileIcon = "🖼️"; // Picture for images
    } else if (['docx', 'doc'].includes(extension)) {
      fileIcon = "📝"; // Note for Word docs
    } else if (['xlsx', 'xls', 'csv'].includes(extension)) {
      fileIcon = "📊"; // Chart for spreadsheets
    } else if (['pptx', 'ppt'].includes(extension)) {
      fileIcon = "📊"; // Chart for presentations
    } else if (['txt', 'log', 'md'].includes(extension)) {
      fileIcon = "📄"; // Page for text
    }
    
    const citationLinks = idMatches
      .map((m) => {
        const rawId = m.slice(2, -1);
        
        // Simplified HTML structure with no newlines or extra whitespace
        return `<a href="#" class="citation-link" data-citation-id="${rawId}" title="View source">${fileIcon} View source</a>`;
      })
      .join(" ");

    return `(Source: ${filenameHtml}, Page: ${pageText}) ${citationLinks}`;
  });
}

// Update the window message event listener to handle both viewers
window.addEventListener('message', function(event) {
  // Process messages from both PDF viewer and document viewer iframes
  if (event.data === 'close-pdf-modal' || event.data === 'close-document-modal') {
    const modal = document.getElementById('citation-modal');
    if (modal) {
      const modalInstance = bootstrap.Modal.getInstance(modal);
      if (modalInstance) {
        modalInstance.hide();
      }
    }
  }
}, false);

function showDocumentInUniversalViewer(data) {
  console.log("Using universal document viewer with data:", data);
  
  // Get or create the modal
  let modal = document.getElementById('citation-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'citation-modal';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = `
      <div class="modal-dialog modal-fullscreen">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body p-0">
            <div class="document-viewer-container" style="width: 100%; height: 90vh;"></div>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
  }
  
  // Set the modal title
  const docName = data.document_source?.name || "Document";
  const docPage = data.document_source?.page || 1;
  const fileType = data.document_source?.file_type || "";
  
  const modalTitle = modal.querySelector('.modal-title');
  if (modalTitle) {
    // Add file type info to the title
    let titleText = `Source: ${docName}, Page: ${docPage}`;
    if (fileType) {
      titleText += ` (${fileType.toUpperCase()})`;
    }
    modalTitle.textContent = titleText;
  }
  
  // Get the container
  const container = modal.querySelector('.document-viewer-container');
  if (!container) {
    console.error("Document viewer container not found");
    return;
  }
  
  // Clear any existing content
  container.innerHTML = '';
  
  // Add a loading indicator
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'spinner-border text-primary';
  loadingDiv.role = 'status';
  loadingDiv.style = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);';
  loadingDiv.innerHTML = '<span class="visually-hidden">Loading...</span>';
  container.appendChild(loadingDiv);
  
  // Create iframe to load the universal document viewer
  const iframe = document.createElement('iframe');
  iframe.src = data.document_viewer_url;
  iframe.style = 'width: 100%; height: 100%; border: none;';
  iframe.allow = 'fullscreen';
  iframe.id = 'document-viewer-iframe';
  
  // When iframe loads, remove the loading indicator
  iframe.onload = function() {
    if (loadingDiv && loadingDiv.parentNode) {
      loadingDiv.parentNode.removeChild(loadingDiv);
    }
  };
  
  // If iframe fails to load, show error
  iframe.onerror = function() {
    console.error("Error loading document viewer iframe");
    container.innerHTML = `
      <div class="alert alert-danger m-3">
        <h4>Error Loading Document</h4>
        <p>There was a problem loading the document. Please try again later.</p>
      </div>
    `;
  };
  
  // Add the iframe to the container
  container.appendChild(iframe);
  
  // Show the modal
  const bsModal = new bootstrap.Modal(modal);
  bsModal.show();
  
  // Update the event listener for messages from the iframe
  window.addEventListener('message', function(event) {
    // Process messages from the document viewer iframe
    if (event.data === 'close-document-modal' || event.data === 'close-pdf-modal') {
      const modal = document.getElementById('citation-modal');
      if (modal) {
        const modalInstance = bootstrap.Modal.getInstance(modal);
        if (modalInstance) {
          modalInstance.hide();
        }
      }
    }
  }, false);
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

function logDocumentSelectionDetails() {
  const searchDocsBtn = document.getElementById("search-documents-btn");
  const isSearchActive = searchDocsBtn && searchDocsBtn.classList.contains("active");
  
  const docScopeSelect = document.getElementById("doc-scope-select");
  const scopeValue = docScopeSelect ? docScopeSelect.value : "none";
  
  const documentSelect = document.getElementById("document-select");
  let selectedDocInfo = "none";
  let selectedDocIsGroup = false;
  let selectedDocGroupId = null;
  let selectedDocGroupName = null;
  
  if (documentSelect && documentSelect.value) {
    const selectedOption = documentSelect.options[documentSelect.selectedIndex];
    selectedDocInfo = {
      id: documentSelect.value,
      label: selectedOption.textContent,
      isGroup: selectedOption.dataset.isGroup === "true"
    };
    
    selectedDocIsGroup = selectedOption.dataset.isGroup === "true";
    selectedDocGroupId = selectedOption.dataset.groupId || null;
    selectedDocGroupName = selectedOption.dataset.groupName || null;
  }
  
  console.group("🔍 Document Selection Details");
  console.log("Document search enabled:", isSearchActive);
  console.log("Scope selection:", scopeValue);
  console.log("Selected document:", selectedDocInfo);
  console.log("Is group document:", selectedDocIsGroup);
  console.log("Group ID:", selectedDocGroupId);
  console.log("Group Name:", selectedDocGroupName);
  console.groupEnd();
  
  return {
    isSearchActive,
    scopeValue,
    selectedDocInfo,
    selectedDocIsGroup,
    selectedDocGroupId,
    selectedDocGroupName
  };
}
// Update the function that handles sending a message with document context
// Enhanced function to handle sending a message, preserving default docs functionality
function actuallySendMessage(textVal) {
  const userInput = document.getElementById("user-input");
  appendMessage("You", textVal);
  if (userInput) userInput.value = "";
  
  console.group("🚀 Sending Message");
  console.log("Message text:", textVal.substring(0, 100) + (textVal.length > 100 ? "..." : ""));
  
  // Get settings for the request with detailed logging
  let hybridSearchEnabled = false;
  const sdbtn = document.getElementById("search-documents-btn");
  if (sdbtn && sdbtn.classList.contains("active")) {
    hybridSearchEnabled = true;
  }
  console.log("Hybrid search enabled:", hybridSearchEnabled);

  let selectedDocumentId = null;
  let documentGroupId = null;
  let docScopeValue = null;
  
  if (hybridSearchEnabled) {
    // Get the full document selection details
    const docDetails = logDocumentSelectionDetails();
    
    const docSel = document.getElementById("document-select");
    if (docSel && docSel.value !== "" && docSel.value !== "All Documents") {
      selectedDocumentId = docSel.value;
      console.log("Selected document ID:", selectedDocumentId);
      
      // Get the selected option to access its data attributes
      const selectedOption = docSel.options[docSel.selectedIndex];
      const isGroupDoc = selectedOption.dataset.isGroup === "true";
      console.log("Is group document:", isGroupDoc);
      
      if (isGroupDoc) {
        // Use the specific group ID from the document instead of active group
        documentGroupId = selectedOption.dataset.groupId;
        console.log("Using specific group document ID:", documentGroupId);
      }
    }
    
    // This part is still needed
    const docScopeSel = document.getElementById("doc-scope-select");
    docScopeValue = docScopeSel ? docScopeSel.value : null;
    console.log("Document scope value:", docScopeValue);
  }

  let bingSearchEnabled = false;
  const wbbtn = document.getElementById("search-web-btn");
  if (wbbtn && wbbtn.classList.contains("active")) {
    bingSearchEnabled = true;
  }
  console.log("Bing search enabled:", bingSearchEnabled);

  let imageGenEnabled = false;
  const igbtn = document.getElementById("image-generate-btn");
  if (igbtn && igbtn.classList.contains("active")) {
    imageGenEnabled = true;
  }
  console.log("Image generation enabled:", imageGenEnabled);
  
  // Create payload
  const payload = {
    message: textVal,
    conversation_id: currentConversationId,
    hybrid_search: hybridSearchEnabled,
    selected_document_id: selectedDocumentId,
    document_group_id: documentGroupId,
    bing_search: bingSearchEnabled,
    image_generation: imageGenEnabled, 
    doc_scope: docScopeValue,
    active_group_id: activeGroupId,
    streaming: true
  };

  // Log the full payload
  console.log("Full payload:", JSON.stringify(payload, null, 2));
  console.groupEnd();
  
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

  // Make the fetch request
  fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
  .then(response => {
    if (!response.ok) {
      // Handle error response
      return response.json().then(errData => {
        throw new Error(errData.error || `HTTP error ${response.status}`);
      }).catch(() => {
        throw new Error(`HTTP error ${response.status}`);
      });
    }
    
    // Check if the response is a streaming response
    const contentType = response.headers.get("Content-Type") || "";
    
    if (contentType.includes("text/event-stream")) {
      // Handle streaming response
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      return processStream();
      
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
              
              // Log completion of the response
              console.log("✅ Streaming complete, final message length:", fullContent.length);
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
                  console.error("Stream error:", data.error);
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
        });
      }
    } else {
      // Not a streaming response, handle as regular JSON
      return response.json().then(data => {
        if (data.error) {
          throw new Error(data.error);
        }
        return data;
      });
    }
  })
  .then(data => {
    if (data && !data.type) {
      // Handle non-streaming response
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
  })
  .catch(error => {
    console.error("Error:", error);
    
    // Remove the streaming message if it exists
    if (messageDiv && messageDiv.parentNode) {
      messageDiv.parentNode.removeChild(messageDiv);
    }
    
    appendMessage("Error", `Could not get a response: ${error.message}`);
  });
}

// Update the window.onload function to properly initialize document selection
window.onload = function() {
  loadConversations();
  setupVoiceToText();

  // First load all documents
  Promise.all([
    loadAllDocs(),
    loadUserPrompts(),
    loadGroupPrompts()
  ])
    .then(() => {
      // Then enable document search after data is loaded
      const searchDocsBtn = document.getElementById("search-documents-btn");
      const docScopeSel = document.getElementById("doc-scope-select");
      const docSelectEl = document.getElementById("document-select");

      if (searchDocsBtn && docScopeSel && docSelectEl) {
        // Set up document scope selection
        setupDocumentScopeSelect();
        
        // Activate document search by default
        searchDocsBtn.classList.add("active");
        docScopeSel.style.display = "inline-block";
        docSelectEl.style.display = "inline-block";
        
        // Make sure to populate the dropdown with the loaded documents
        setTimeout(() => {
          populateDocumentSelectScope();
        }, 100); // Small delay to ensure UI updates
      }
    })
    .catch((err) => {
      console.error("Error loading initial data:", err);
    });
};


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
        <div class="toast-body">${message}</div>
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


window.addEventListener('message', function(event) {
  // Process messages from the PDF viewer iframe
  if (event.data === 'close-pdf-modal') {
    const modal = document.getElementById('citation-modal');
    if (modal) {
      const modalInstance = bootstrap.Modal.getInstance(modal);
      if (modalInstance) {
        modalInstance.hide();
      }
    }
  }
}, false);

// Add a fix for modal backdrop issues
document.addEventListener('DOMContentLoaded', function() {
  // Add event handler for all modals to ensure proper cleanup
  document.querySelectorAll('.modal').forEach(function(modalEl) {
    modalEl.addEventListener('hidden.bs.modal', function() {
      // Remove any lingering modal backdrops
      const backdrops = document.querySelectorAll('.modal-backdrop');
      backdrops.forEach(function(backdrop) {
        backdrop.remove();
      });
      
      // Re-enable scrolling
      document.body.classList.remove('modal-open');
      document.body.style.overflow = '';
      document.body.style.paddingRight = '';
    });
  });
});

// Update this in your chats.js file



// Function to show an error in a popup when we can't get the document
function showErrorPopup(errorTitle, errorDetails, documentSource) {
  let modalContainer = document.getElementById("citation-modal");
  if (!modalContainer) {
    modalContainer = document.createElement("div");
    modalContainer.id = "citation-modal";
    modalContainer.classList.add("modal", "fade");
    modalContainer.tabIndex = -1;
    modalContainer.setAttribute("aria-hidden", "true");

    modalContainer.innerHTML = `
      <div class="modal-dialog modal-dialog-scrollable modal-lg">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title" id="citationModalLabel">Citation Error</h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body">
            <div id="citation-error-content" class="alert alert-warning"></div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modalContainer);
  } else {
    const modalTitle = modalContainer.querySelector(".modal-title");
    if (modalTitle) {
      modalTitle.textContent = `Citation Error`;
    }
  }

  const errorContent = document.getElementById("citation-error-content") || 
                      modalContainer.querySelector(".modal-body");
  
  if (errorContent) {
    // Create informative error message
    let errorHtml = `
      <div class="alert alert-warning">
        <h4>${errorTitle}</h4>
        <p>${errorDetails}</p>
    `;
    
    // Add document source info if available
    if (documentSource) {
      errorHtml += `
        <hr>
        <p>
          <strong>Document:</strong> ${documentSource.name || 'Unknown'}<br>
          <strong>Page:</strong> ${documentSource.page || '0'}<br>
          <strong>Workspace:</strong> ${documentSource.workspace_type || 'Unknown'}
        </p>
      `;
    }
    
    errorHtml += `
        <p class="mt-3">
          <small>You can try the following:</small>
          <ul>
            <li>Reload the page and try again</li>
            <li>Go to your documents workspace to view the document directly</li>
            <li>Contact support if the issue persists</li>
          </ul>
        </p>
      </div>
    `;
    
    errorContent.innerHTML = errorHtml;
  }

  const modal = new bootstrap.Modal(modalContainer);
  modal.show();
}

// Updated showDocumentInIframe function to use the page number
function showDocumentInIframe(documentUrl, documentName, pageNumber) {
  console.log(`Showing document: ${documentName}, page: ${pageNumber}`); 
  
  if (!documentUrl) {
    console.error("Missing document URL");
    showToast("Error: Document URL not available", "danger");
    return;
  }
  
  // Get or create the modal
  let modal = document.getElementById('citation-modal');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'citation-modal';
    modal.className = 'modal fade';
    modal.setAttribute('tabindex', '-1');
    modal.setAttribute('aria-hidden', 'true');
    
    modal.innerHTML = `
      <div class="modal-dialog modal-fullscreen">
        <div class="modal-content">
          <div class="modal-header">
            <h5 class="modal-title"></h5>
            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
          </div>
          <div class="modal-body p-0">
            <div class="document-viewer-container" style="width: 100%; height: 90vh;"></div>
          </div>
        </div>
      </div>
    `;
    
    document.body.appendChild(modal);
  }
  
  // Set the modal title with exact page number
  const modalTitle = modal.querySelector('.modal-title');
  if (modalTitle) {
    modalTitle.textContent = `Source: ${documentName}, Page: ${pageNumber}`;
  }
  
  // Get the container
  const container = modal.querySelector('.document-viewer-container');
  if (!container) {
    console.error("Document viewer container not found");
    return;
  }
  
  // Clear any existing content
  container.innerHTML = '';
  
  // Add a loading indicator
  const loadingDiv = document.createElement('div');
  loadingDiv.className = 'spinner-border text-primary';
  loadingDiv.role = 'status';
  loadingDiv.style = 'position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);';
  loadingDiv.innerHTML = '<span class="visually-hidden">Loading...</span>';
  container.appendChild(loadingDiv);
  
  // Create the proxy URL for the document
  const proxyUrl = `/document-proxy?url=${encodeURIComponent(documentUrl)}`;
  
  // Create the PDF viewer URL with the exact page number
  const randomParam = Math.floor(Math.random() * 1000000);
  // In showDocumentInIframe function in chats.js
  const viewerUrl = `/pdf-viewer?file=${encodeURIComponent(proxyUrl)}&page=${pageNumber}&zoom=100&nocache=${randomParam}`;
  
  console.log("PDF Viewer URL:", viewerUrl);
  
  // Create iframe to load the PDF viewer
  const iframe = document.createElement('iframe');
  iframe.src = viewerUrl;
  iframe.style = 'width: 100%; height: 100%; border: none;';
  iframe.allow = 'fullscreen';
  iframe.id = 'pdf-iframe';
  
  // When iframe loads, remove the loading indicator
  iframe.onload = function() {
    if (loadingDiv && loadingDiv.parentNode) {
      loadingDiv.parentNode.removeChild(loadingDiv);
    }
  };
  
  // If iframe fails to load, show error
  iframe.onerror = function() {
    console.error("Error loading PDF iframe");
    container.innerHTML = `
      <div class="alert alert-danger m-3">
        <h4>Error Loading Document</h4>
        <p>There was a problem loading the PDF. Please try again later.</p>
      </div>
    `;
  };
  
  // Add the iframe to the container
  container.appendChild(iframe);
  
  // Show the modal
  const bsModal = new bootstrap.Modal(modal);
  bsModal.show();
}
// Add this to your chats.js file

function setupVoiceToText() {
  const userInput = document.getElementById('user-input');
  const voiceButton = document.getElementById('voice-input-btn');
  
  // Check if browser supports speech recognition
  if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
    console.log('Speech recognition not supported in this browser');
    if (voiceButton) {
      voiceButton.style.display = 'none';
    }
    return;
  }
  
  // Initialize speech recognition
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  
  recognition.continuous = false;
  recognition.interimResults = false; // Changed to false to avoid duplicates
  recognition.lang = 'en-US';
  
  let isRecognizing = false;
  
  // When speech recognition results are available
  recognition.onresult = (event) => {
    if (event.results.length > 0) {
      const transcript = event.results[0][0].transcript;
      
      // Update the input field with the recognized text
      if (userInput) {
        // Clear any existing value to prevent duplication
        userInput.value = transcript;
      }
    }
  };
  
  // When speech recognition ends
  recognition.onend = () => {
    isRecognizing = false;
    if (voiceButton) {
      voiceButton.classList.remove('listening');
      // Update the icon to show it's no longer listening
      const icon = voiceButton.querySelector('i');
      if (icon) {
        icon.classList.remove('bi-mic-fill');
        icon.classList.add('bi-mic');
      }
    }
  };
  
  // Handle errors
  recognition.onerror = (event) => {
    console.error('Speech recognition error:', event.error);
    isRecognizing = false;
    if (voiceButton) {
      voiceButton.classList.remove('listening');
      // Update the icon to show it's no longer listening
      const icon = voiceButton.querySelector('i');
      if (icon) {
        icon.classList.remove('bi-mic-fill');
        icon.classList.add('bi-mic');
      }
    }
    
    // Show a more user-friendly error message
    if (event.error === 'network') {
      showToast("Network error. Please check your internet connection.", "danger");
    } else if (event.error === 'not-allowed') {
      showToast("Microphone access denied. Please allow microphone access.", "danger");
    } else if (event.error === 'aborted') {
      showToast("Speech recognition was aborted.", "warning");
    } else {
      showToast(`Speech recognition error: ${event.error}`, "danger");
    }
  };
  
  // Toggle speech recognition when voice button is clicked
  if (voiceButton) {
    voiceButton.addEventListener('click', () => {
      if (isRecognizing) {
        recognition.stop();
        isRecognizing = false;
        voiceButton.classList.remove('listening');
        // Update the icon to show it's no longer listening
        const icon = voiceButton.querySelector('i');
        if (icon) {
          icon.classList.remove('bi-mic-fill');
          icon.classList.add('bi-mic');
        }
      } else {
        // Empty the input field before starting recognition
        if (userInput) {
          userInput.value = '';
        }
        
        recognition.start();
        isRecognizing = true;
        voiceButton.classList.add('listening');
        // Update the icon to show it's listening
        const icon = voiceButton.querySelector('i');
        if (icon) {
          icon.classList.remove('bi-mic');
          icon.classList.add('bi-mic-fill');
        }
      }
    });
  }
}

window.onload = function() {
  loadConversations();
  setupVoiceToText();

  // First load all documents
  Promise.all([
    loadAllDocs(),
    loadUserPrompts(),
    loadGroupPrompts()
  ])
    .then(() => {
      // Then enable document search after data is loaded
      const searchDocsBtn = document.getElementById("search-documents-btn");
      const docScopeSel = document.getElementById("doc-scope-select");
      const docSelectEl = document.getElementById("document-select");

      if (searchDocsBtn && docScopeSel && docSelectEl) {
        // Set up document scope selection
        setupDocumentScopeSelect();
        
        // Activate document search by default
        searchDocsBtn.classList.add("active");
        docScopeSel.style.display = "inline-block";
        docSelectEl.style.display = "inline-block";
        
        // Make sure to populate the dropdown with the loaded documents
        setTimeout(() => {
          populateDocumentSelectScope();
        }, 100); // Small delay to ensure UI updates
      }
    })
    .catch((err) => {
      console.error("Error loading initial data:", err);
    });
};

// Add CSS classes for the voice button states
// This can be added inline or in your CSS file
document.head.insertAdjacentHTML('beforeend', `
  <style>
    #voice-input-btn {
      transition: all 0.2s ease;
    }
    #voice-input-btn.listening {
      color: #dc3545;
      animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
      0% { transform: scale(1); }
      50% { transform: scale(1.1); }
      100% { transform: scale(1); }
    }
  </style>
`);


// Update this function in your chats.js file 
// to handle citations with Office document integration

// Update this function in your chats.js file to use the new MS Graph document viewer

function handleCitationClick(citationId) {
  // Show loading indicator
  showToast('Loading document...', 'info');

  // Prepare request data with citation ID
  const requestData = {
    citation_id: citationId
  };
  
  // Add the specific group ID if known
  const docSel = document.getElementById("document-select");
  if (docSel && docSel.value) {
    const selectedOption = docSel.options[docSel.selectedIndex];
    if (selectedOption.dataset.isGroup === "true") {
      requestData.doc_group_id = selectedOption.dataset.groupId;
    }
  }
  
  // Make the request to get citation details
  fetch('/api/get_citation', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestData)
  })
  .then(response => response.json())
  .then(data => {
    if (data.error) {
      showToast('Error: ' + data.error, 'danger');
      return;
    }
    
    // Set modal title
    const sourceName = data.document_source.name || 'Document';
    const sourcePage = data.document_source.page || 1;
    document.getElementById('citationModalLabel').textContent = 
        `${sourceName} (Page ${sourcePage})`;
    
    // Create iframe for document viewer
    const container = document.querySelector('.document-viewer-container');
    container.innerHTML = ''; // Clear any existing content
    
    if (data.document_viewer_url) {
      const iframe = document.createElement('iframe');
      iframe.style.width = '100%';
      iframe.style.height = '85vh';
      iframe.style.border = 'none';
      iframe.src = data.document_viewer_url;
      container.appendChild(iframe);
    } else {
      // Fallback to displaying text
      const textContainer = document.createElement('div');
      textContainer.style.padding = '20px';
      textContainer.style.backgroundColor = '#f8f9fa';
      textContainer.style.border = '1px solid #dee2e6';
      textContainer.style.borderRadius = '4px';
      textContainer.style.margin = '20px';
      textContainer.style.maxHeight = '80vh';
      textContainer.style.overflow = 'auto';
      textContainer.style.whiteSpace = 'pre-wrap';
      
      const header = document.createElement('h6');
      header.textContent = 'Cited Text:';
      header.style.marginBottom = '10px';
      
      const text = document.createElement('div');
      text.textContent = data.cited_text || 'No text available';
      
      textContainer.appendChild(header);
      textContainer.appendChild(text);
      container.appendChild(textContainer);
    }
    
    // Show the citation modal
    const citationModal = new bootstrap.Modal(document.getElementById('citation-modal'));
    citationModal.show();
  })
  .catch(error => {
    console.error('Error fetching citation:', error);
    showToast('Error loading document citation', 'danger');
  });
}

// Function to check for document preview URL using Microsoft Graph
function checkDocumentPreview(documentUrl, fileName, fileType, pageNumber, container) {
  // Show loading indicator in the container
  container.innerHTML = `
      <div style="display: flex; justify-content: center; align-items: center; height: 85vh; flex-direction: column;">
          <div class="spinner-border text-primary mb-3" role="status">
              <span class="visually-hidden">Generating document preview...</span>
          </div>
          <div>Generating document preview...</div>
      </div>
  `;
  
  // Request a document preview from our API
  fetch('/api/get_document_preview', {
      method: 'POST',
      headers: {
          'Content-Type': 'application/json'
      },
      body: JSON.stringify({
          document_url: documentUrl,
          file_name: fileName
      })
  })
  .then(response => response.json())
  .then(data => {
      if (data.error) {
          console.error('Preview error:', data.error);
          // Fallback to download view if there's an error
          showFallbackView({
              document_source: {
                  name: fileName,
                  page: pageNumber,
                  file_type: fileType
              },
              cited_text: "Unable to display document preview. Please download the document to view it.",
              download_url: data.download_url || documentUrl
          }, fileName, pageNumber, fileType, container);
          return;
      }
      
      if (data.preview_url && data.preview_type === 'ms_graph') {
          // Create iframe for MS Graph preview
          const iframe = document.createElement('iframe');
          iframe.style.width = '100%';
          iframe.style.height = '85vh';
          iframe.style.border = 'none';
          iframe.src = `/ms-graph-document-viewer?preview_url=${encodeURIComponent(data.preview_url)}&name=${encodeURIComponent(fileName)}&type=${fileType}&page=${pageNumber}`;
          
          // Replace loading indicator with iframe
          container.innerHTML = '';
          container.appendChild(iframe);
          
          // Listen for messages from the iframe
          window.addEventListener('message', function(event) {
              if (event.data === 'close-document-modal') {
                  // Close the modal when receiving this message
                  bootstrap.Modal.getInstance(document.getElementById('citation-modal')).hide();
              }
          });
      }
      else if (data.preview_url && data.preview_type === 'direct') {
          // Direct preview URL (for PDFs, etc.)
          const iframe = document.createElement('iframe');
          iframe.style.width = '100%';
          iframe.style.height = '85vh';
          iframe.style.border = 'none';
          iframe.src = data.preview_url;
          
          // Replace loading indicator with iframe
          container.innerHTML = '';
          container.appendChild(iframe);
      }
      else {
          // Fallback if no preview is available
          showFallbackView({
              document_source: {
                  name: fileName,
                  page: pageNumber,
                  file_type: fileType
              },
              cited_text: "Unable to display document preview. Please download the document to view it.",
              download_url: documentUrl
          }, fileName, pageNumber, fileType, container);
      }
  })
  .catch(error => {
      console.error('Error getting document preview:', error);
      // Fallback to download view if there's an exception
      showFallbackView({
          document_source: {
              name: fileName,
              page: pageNumber,
              file_type: fileType
          },
          cited_text: "An error occurred while generating the document preview. Please download the document to view it.",
          download_url: documentUrl
      }, fileName, pageNumber, fileType, container);
  });
}

// Function to show fallback view when document can't be previewed
function showFallbackView(data, sourceName, sourcePage, fileType, container) {
  // Create a better UI for fallback view
  const infoBox = document.createElement('div');
  infoBox.className = 'p-4 bg-light rounded shadow-sm';
  infoBox.style.maxWidth = '600px';
  infoBox.style.margin = '50px auto';
  infoBox.style.textAlign = 'center';
  
  // Add document icon
  let iconClass = 'bi-file-text';
  if (fileType === 'docx' || fileType === 'doc') iconClass = 'bi-file-earmark-word text-primary';
  else if (fileType === 'xlsx' || fileType === 'xls') iconClass = 'bi-file-earmark-excel text-success';
  else if (fileType === 'pptx' || fileType === 'ppt') iconClass = 'bi-file-earmark-ppt text-danger';
  
  const docIcon = document.createElement('div');
  docIcon.innerHTML = `<i class="${iconClass}" style="font-size: 4rem;"></i>`;
  
  // Add document info
  const docInfo = document.createElement('div');
  docInfo.className = 'mt-3 mb-4';
  docInfo.innerHTML = `
      <h4>${sourceName}</h4>
      <p class="text-muted">This document is on page ${sourcePage}</p>
      <div class="alert alert-info">
          This document cannot be displayed directly in the browser. 
          Please download it to view the full content.
      </div>
  `;
  
  // Add download button if URL is available
  const actionSection = document.createElement('div');
  actionSection.className = 'mb-4';
  
  if (data.download_url) {
      const downloadBtn = document.createElement('a');
      downloadBtn.href = data.download_url;
      downloadBtn.className = 'btn btn-primary btn-lg';
      downloadBtn.download = sourceName;
      downloadBtn.innerHTML = '<i class="bi bi-download me-2"></i>Download Original Document';
      actionSection.appendChild(downloadBtn);
  }
  
  // Add cited text section
  const citedTextSection = document.createElement('div');
  citedTextSection.className = 'mt-4 p-3 bg-white border rounded text-start';
  citedTextSection.innerHTML = `
      <h6>Cited Text:</h6>
      <div style="white-space: pre-wrap;">${data.cited_text || 'No text available'}</div>
  `;
  
  // Assemble the components
  infoBox.appendChild(docIcon);
  infoBox.appendChild(docInfo);
  infoBox.appendChild(actionSection);
  infoBox.appendChild(citedTextSection);
  
  // Replace container content
  container.innerHTML = '';
  container.appendChild(infoBox);
}

// Helper toast function if not already defined
function showToast(message, type = 'info') {
  const toastContainer = document.getElementById('toast-container');
  if (!toastContainer) return;
  
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${type} border-0`;
  toast.setAttribute('role', 'alert');
  toast.setAttribute('aria-live', 'assertive');
  toast.setAttribute('aria-atomic', 'true');
  
  toast.innerHTML = `
      <div class="d-flex">
          <div class="toast-body">
              ${message}
          </div>
          <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
  `;
  
  toastContainer.appendChild(toast);
  const bsToast = new bootstrap.Toast(toast, {
      autohide: true,
      delay: 3000
  });
  bsToast.show();
  
  // Remove the toast element after it's hidden
  toast.addEventListener('hidden.bs.toast', function() {
      toast.remove();
  });
}

// Update the event delegation for citation links in chats.js
document.addEventListener('click', function(event) {
  // Find closest citation link
  const citationLink = event.target.closest('.citation-link');
  if (citationLink) {
      event.preventDefault();
      const citationId = citationLink.getAttribute('data-citation-id');
      if (citationId) {
          handleCitationClick(citationId);
      }
  }
});



function enhanceSearchDocumentsBtn() {
  const searchDocumentsBtn = document.getElementById("search-documents-btn");
  if (!searchDocumentsBtn) return;
  
  // Replace with enhanced version
  searchDocumentsBtn.addEventListener("click", function() {
    console.group("🔎 Document Search Button Toggle");
    
    const wasActive = this.classList.contains("active");
    console.log("Was active before click:", wasActive);
    
    // Toggle active state
    this.classList.toggle("active");
    const isNowActive = this.classList.contains("active");
    console.log("Is active after click:", isNowActive);

    const docScopeSel = document.getElementById("doc-scope-select");
    const docSelectEl = document.getElementById("document-select");
    if (!docScopeSel || !docSelectEl) {
      console.warn("Document scope or select elements not found");
      console.groupEnd();
      return;
    }

    if (isNowActive) {
      console.log("Enabling document selection UI");
      docScopeSel.style.display = "inline-block";
      docSelectEl.style.display = "inline-block";
      
      // Load personal and group documents if needed
      console.log("Loading documents...");
      const personalLoaded = personalDocs.length > 0;
      const groupLoaded = groupDocs.length > 0;
      
      console.log("Personal docs already loaded:", personalLoaded, "count:", personalDocs.length);
      console.log("Group docs already loaded:", groupLoaded, "count:", groupDocs.length);
      
      if (!personalLoaded || !groupLoaded) {
        console.log("Need to load documents, calling loadAllDocs()");
        loadAllDocs().then(() => {
          console.log("Documents loaded, populating document select");
          setupDocumentScopeSelect();
          populateDocumentSelectScope();
        });
      } else {
        console.log("Documents already loaded, populating document select");
        setupDocumentScopeSelect();
        populateDocumentSelectScope();
      }
    } else {
      console.log("Disabling document selection UI");
      docScopeSel.style.display = "none";
      docSelectEl.style.display = "none";
      docSelectEl.innerHTML = "";
    }
    
    console.groupEnd();
  });
}

// Call this function after DOM is loaded
document.addEventListener("DOMContentLoaded", function() {
  enhanceSearchDocumentsBtn();
});