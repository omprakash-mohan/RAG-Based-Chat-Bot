const API = "http://127.0.0.1:8000";

const dropZone = document.getElementById("drop-zone");
const fileInput = document.getElementById("file-input");
const fileList = document.getElementById("file-list");
const clearDocsBtn = document.getElementById("clear-docs");

const memoryInput = document.getElementById("memory-input");
const saveMemoryBtn = document.getElementById("save-memory-btn");
const clearMemoryBtn = document.getElementById("clear-memory-btn");
const refreshMemoryBtn = document.getElementById("refresh-memory-btn");
const memoryList = document.getElementById("memory-list");

const toolsToggle = document.getElementById("tools-toggle");
const toolsArrow = document.getElementById("tools-arrow");
const smartTools = document.getElementById("smart-tools");
const generateSuggestionsBtn = document.getElementById("generate-suggestions-btn");
const generateQuizBtn = document.getElementById("generate-quiz-btn");
const exportPdfBtn = document.getElementById("export-pdf-btn");
const saveNotesBtn = document.getElementById("save-notes-btn");
const suggestionsList = document.getElementById("suggestions-list");

const summaryButtons = document.getElementById("summary-buttons");
const pagePicker = document.getElementById("page-picker");
const pageNumberInput = document.getElementById("page-number");
const toolCloseBtn = document.getElementById("tool-close");

const questionInput = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const chatBox = document.getElementById("chat-box");

const quizModal = document.getElementById("quiz-output");
const quizContent = document.getElementById("quiz-content");
const closeQuizBtn = document.getElementById("close-quiz");

let currentFiles = [];
let selectedSummaryMode = null; // full | page | keypoints | null
let editingMemoryId = null;

const TOOL_HINTS = {
  full: "Summarize entire uploaded document in a clear structure.",
  page: "Page Info mode is active. Enter a page number and press Enter.",
  keypoints: "List key points from the uploaded document.",
  default: "Ask a question about your documents..."
};

function setCollapsedTools(collapsed) {
  smartTools.classList.toggle("hidden", collapsed);
  toolsArrow.style.transform = collapsed ? "rotate(-90deg)" : "rotate(0deg)";
  localStorage.setItem("smartToolsCollapsed", String(collapsed));
}

function toggleTools() {
  const collapsed = !smartTools.classList.contains("hidden");
  setCollapsedTools(collapsed);
}

function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

["dragenter", "dragover", "dragleave", "drop"].forEach(evt => {
  dropZone.addEventListener(evt, preventDefaults, false);
});

["dragenter", "dragover"].forEach(evt => {
  dropZone.addEventListener(evt, () => dropZone.classList.add("drag-over"), false);
});
["dragleave", "drop"].forEach(evt => {
  dropZone.addEventListener(evt, () => dropZone.classList.remove("drag-over"), false);
});

dropZone.addEventListener("drop", (e) => handleFiles(e.dataTransfer.files));
fileInput.addEventListener("change", function () {
  handleFiles(this.files);
  this.value = "";
});

function isSupportedFile(file) {
  const name = (file.name || "").toLowerCase();
  return [
    ".pdf", ".doc", ".docx", ".txt", ".md", ".csv", ".json",
    ".xls", ".xlsx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"
  ].some(ext => name.endsWith(ext));
}

function iconForFile(fileName) {
  const lower = fileName.toLowerCase();
  if (lower.endsWith(".pdf")) return "fa-file-pdf";
  if (lower.endsWith(".doc") || lower.endsWith(".docx")) return "fa-file-word";
  if (lower.endsWith(".xls") || lower.endsWith(".xlsx")) return "fa-file-excel";
  if (lower.endsWith(".ppt") || lower.endsWith(".pptx")) return "fa-file-powerpoint";
  if (lower.endsWith(".csv")) return "fa-file-csv";
  if (lower.endsWith(".json")) return "fa-brackets-curly";
  if (/\.(png|jpg|jpeg|webp|bmp|gif)$/.test(lower)) return "fa-file-image";
  return "fa-file-lines";
}

function handleFiles(files) {
  if (!files || files.length === 0) return;

  let added = 0;
  for (const file of files) {
    if (!isSupportedFile(file)) {
      appendMessage("bot", `Sorry, I cannot use "${file.name}". Please upload a PDF, document, spreadsheet, PowerPoint, or image.`);
      continue;
    }
    currentFiles.push(file);
    added++;
  }

  if (added > 0) {
    renderFiles();
    requestSuggestions(true);
    enableChat();
  }
}

function renderFiles() {
  fileList.innerHTML = "";

  if (currentFiles.length === 0) {
    fileList.style.display = "none";
    clearDocsBtn.style.display = "none";
    return;
  }

  fileList.style.display = "flex";
  clearDocsBtn.style.display = "block";

  currentFiles.forEach((file, index) => {
    const row = document.createElement("div");
    row.className = "file-item";
    row.innerHTML = `
      <i class="fa-solid ${iconForFile(file.name)}"></i>
      <div class="file-name" title="${file.name}">${file.name}</div>
      <i class="fa-solid fa-xmark file-del" title="Remove"></i>
    `;
    row.querySelector(".file-del").addEventListener("click", () => removeFile(index));
    fileList.appendChild(row);
  });
}

function removeFile(index) {
  currentFiles.splice(index, 1);
  renderFiles();
}

function createFilesFormData(extra = {}) {
  const formData = new FormData();
  currentFiles.forEach(file => formData.append("files", file));
  Object.entries(extra).forEach(([k, v]) => formData.append(k, v));
  return formData;
}

async function postForm(endpoint, formData) {
  const res = await fetch(`${API}${endpoint}`, {
    method: "POST",
    body: formData
  });

  let data;
  try {
    data = await res.json();
  } catch (e) {
    const text = await res.text();
    throw new Error(`Server returned non-JSON response: ${res.status} ${text.slice(0, 100)}`);
  }

  if (!res.ok) {
    const detail = data?.detail || data?.message || `Server error: ${res.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}

function getResponseText(data) {
  if (!data) return "No answer returned.";
  if (typeof data === "string") return data;
  if (typeof data.answer === "string" && data.answer.trim()) return data.answer;
  if (typeof data.quiz === "string" && data.quiz.trim()) return data.quiz;
  if (Array.isArray(data.questions)) return data.questions.join("\n");
  return "No answer returned.";
}

function appendMessage(sender, text) {
  const row = document.createElement("div");
  row.className = `message ${sender === "user" ? "user" : "bot"}`;

  if (sender === "user") {
    row.innerHTML = `<div class="bubble">${escapeHtml(text)}</div>`;
  } else {
    row.innerHTML = `
      <div class="avatar"><i class="fa-solid fa-robot"></i></div>
      <div class="bubble">${escapeHtml(text)}</div>
    `;
  }

  chatBox.appendChild(row);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function showTyping() {
  const id = `typing-${Date.now()}`;
  const row = document.createElement("div");
  row.className = "message bot";
  row.id = id;
  row.innerHTML = `
    <div class="avatar"><i class="fa-solid fa-robot"></i></div>
    <div class="bubble">Typing...</div>
  `;
  chatBox.appendChild(row);
  chatBox.scrollTop = chatBox.scrollHeight;
  return id;
}

function removeElement(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function escapeHtml(text) {
  return String(text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function enableChat() {
  questionInput.disabled = false;
  sendBtn.disabled = false;
}

function disableChat() {
  questionInput.disabled = true;
  sendBtn.disabled = true;
}

function renderMemory(items) {
  memoryList.innerHTML = "";

  if (!items || items.length === 0) {
    memoryList.innerHTML = `<div class="muted" style="font-size:12px;">No memory saved yet.</div>`;
    return;
  }

  items.forEach(item => {
    const row = document.createElement("div");
    row.className = "memory-item";
    row.innerHTML = `
      <div class="memory-text">${escapeHtml(item.text)}</div>
      <div class="memory-actions">
        <button type="button" data-edit="${item.id}">Edit</button>
        <button type="button" data-delete="${item.id}">Delete</button>
      </div>
    `;
    row.querySelector('[data-edit]').addEventListener("click", () => {
      editingMemoryId = item.id;
      memoryInput.value = item.text;
      memoryInput.focus();
    });
    row.querySelector('[data-delete]').addEventListener("click", () => deleteMemory(item.id));
    memoryList.appendChild(row);
  });
}

async function loadMemory() {
  try {
    const res = await fetch(`${API}/memory`);
    const data = await res.json();
    renderMemory(data.items || []);
  } catch (e) {
    renderMemory([]);
  }
}

async function saveMemory() {
  const text = (memoryInput.value || "").trim();
  if (!text) {
    appendMessage("bot", "Please type something to remember first.");
    return;
  }

  const formData = new FormData();
  formData.append("text", text);
  if (editingMemoryId) formData.append("memory_id", editingMemoryId);

  try {
    const data = await postForm("/memory", formData);
    renderMemory(data.items || []);
    memoryInput.value = "";
    editingMemoryId = null;
    appendMessage("bot", "Memory saved successfully.");
  } catch (e) {
    appendMessage("bot", `Could not save memory: ${e.message}`);
  }
}

async function deleteMemory(id) {
  try {
    const res = await fetch(`${API}/memory/${id}`, { method: "DELETE" });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || "Failed to delete memory.");
    renderMemory(data.items || []);
    if (editingMemoryId === id) {
      editingMemoryId = null;
      memoryInput.value = "";
    }
  } catch (e) {
    appendMessage("bot", `Could not delete memory: ${e.message}`);
  }
}

async function clearAllMemory() {
  try {
    const res = await fetch(`${API}/memory/clear`, { method: "POST" });
    const data = await res.json();
    if (!res.ok) throw new Error(data?.detail || "Failed to clear memory.");
    editingMemoryId = null;
    memoryInput.value = "";
    renderMemory(data.items || []);
    appendMessage("bot", "All memory cleared.");
  } catch (e) {
    appendMessage("bot", `Could not clear memory: ${e.message}`);
  }
}

function setSummaryMode(mode) {
  if (selectedSummaryMode === mode) {
    selectedSummaryMode = null;
  } else {
    selectedSummaryMode = mode;
  }
  renderSummaryModeUI();
}

function clearSummaryMode() {
  selectedSummaryMode = null;
  renderSummaryModeUI();
}

function renderSummaryModeUI() {
  document.querySelectorAll(".mode-btn").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === selectedSummaryMode);
  });

  pagePicker.classList.toggle("hidden", selectedSummaryMode !== "page");
  toolCloseBtn.classList.toggle("hidden", !selectedSummaryMode);

  if (selectedSummaryMode === "full") {
    questionInput.placeholder = TOOL_HINTS.full;
  } else if (selectedSummaryMode === "page") {
    questionInput.placeholder = TOOL_HINTS.page;
  } else if (selectedSummaryMode === "keypoints") {
    questionInput.placeholder = TOOL_HINTS.keypoints;
  } else {
    questionInput.placeholder = TOOL_HINTS.default;
  }
}

async function runTool(endpoint, extraFields = {}, userLabel = "") {
  if (userLabel) appendMessage("user", userLabel);

  const typingId = showTyping();
  try {
    const data = await postForm(endpoint, createFilesFormData(extraFields));
    removeElement(typingId);
    appendMessage("bot", getResponseText(data));
    return data;
  } catch (e) {
    removeElement(typingId);
    appendMessage("bot", `Request failed: ${e.message}`);
    return null;
  }
}

async function askQuestion() {
  const q = (questionInput.value || "").trim();
  if (!q) return;

  appendMessage("user", q);
  questionInput.value = "";
  disableChat();

  const typingId = showTyping();
  try {
    const formData = createFilesFormData({ question: q });
    const data = await postForm("/ask", formData);
    removeElement(typingId);
    appendMessage("bot", getResponseText(data));
  } catch (e) {
    removeElement(typingId);
    appendMessage("bot", `Request failed: ${e.message}`);
  } finally {
    enableChat();
  }
}

async function requestSuggestions(announce = false) {
  const typingId = announce ? showTyping() : null;
  try {
    const data = await postForm("/suggest-questions", createFilesFormData());
    const questions = Array.isArray(data.questions) ? data.questions : [];

    const unique = [...new Set([
      "What is the objective?",
      "What is methodology?",
      "What is conclusion?",
      ...questions
    ])].slice(0, 8);

    suggestionsList.innerHTML = "";
    if (unique.length === 0) {
      suggestionsList.innerHTML = `<div class="muted" style="font-size:12px;">No suggestions available.</div>`;
    } else {
      unique.forEach(q => {
        const chip = document.createElement("button");
        chip.className = "suggestion-chip";
        chip.type = "button";
        chip.textContent = q;
        chip.addEventListener("click", () => {
          questionInput.value = q;
          questionInput.focus();
        });
        suggestionsList.appendChild(chip);
      });
    }

    if (announce) appendMessage("bot", "Here are some useful questions you can try.");
  } catch (e) {
    suggestionsList.innerHTML = `
      <button class="suggestion-chip" type="button">What is the objective?</button>
      <button class="suggestion-chip" type="button">What is methodology?</button>
      <button class="suggestion-chip" type="button">What is conclusion?</button>
    `;
    if (announce) appendMessage("bot", `Could not generate suggestions: ${e.message}`);
  } finally {
    if (typingId) removeElement(typingId);
  }
}

function buildPageNumber() {
  const page = parseInt(pageNumberInput.value || "", 10);
  return Number.isFinite(page) && page > 0 ? page : null;
}

async function handleToolButton(mode) {
  if (selectedSummaryMode === mode) {
    clearSummaryMode();
    return;
  }

  selectedSummaryMode = mode;
  renderSummaryModeUI();

  if (mode === "page") {
    appendMessage("bot", "Page Info mode is active. Enter a page number in the box and press Enter.");
    pageNumberInput.focus();
    return;
  }

  if (mode === "full") {
    await runTool("/summarize", {}, "Summarize");
  } else if (mode === "keypoints") {
    await runTool("/keypoints", {}, "Key Points");
  }
}

async function generateQuiz() {
  if (quizModal) {
    quizModal.classList.remove("hidden");
    quizContent.textContent = "Generating quiz...";
  }

  try {
    const data = await postForm("/generate-quiz", createFilesFormData({ count: "5" }));
    quizContent.textContent = getResponseText(data);
    appendMessage("bot", "Quiz generated successfully. You can review it in the quiz panel.");
  } catch (e) {
    quizContent.textContent = `Quiz generation failed: ${e.message}`;
    appendMessage("bot", `Quiz generation failed: ${e.message}`);
  }
}

function exportChatPdf() {
  const chatLines = Array.from(chatBox.querySelectorAll(".message")).map(msg => {
    const isUser = msg.classList.contains("user");
    const role = isUser ? "You" : "Bot";
    const text = msg.querySelector(".bubble")?.textContent?.trim() || "";
    return `${role}: ${text}`;
  });

  if (!chatLines.length) {
    appendMessage("bot", "No chat content available to export.");
    return;
  }

  if (!window.jspdf || !window.jspdf.jsPDF) {
    appendMessage("bot", "PDF library is not available. Try refreshing the page.");
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF();
  const margin = 12;
  const pageWidth = doc.internal.pageSize.getWidth() - (margin * 2);
  let y = 16;

  doc.setFontSize(14);
  doc.text("Chat Export", margin, y);
  y += 10;
  doc.setFontSize(10);

  chatLines.forEach(line => {
    const wrapped = doc.splitTextToSize(line, pageWidth);
    if (y + wrapped.length * 6 > 280) {
      doc.addPage();
      y = 16;
    }
    doc.text(wrapped, margin, y);
    y += wrapped.length * 6 + 2;
  });

  doc.save("chat_export.pdf");
}

function saveNotes() {
  const notes = Array.from(chatBox.querySelectorAll(".message.bot .bubble"))
    .map(n => n.textContent.trim())
    .filter(Boolean)
    .join("\n\n");

  if (!notes) {
    appendMessage("bot", "No assistant answers available to save as notes.");
    return;
  }

  const blob = new Blob([notes], { type: "text/plain;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "study_notes.txt";
  a.click();
  URL.revokeObjectURL(a.href);
}

clearDocsBtn.addEventListener("click", async () => {
  currentFiles = [];
  renderFiles();
  questionInput.value = "";
  pageNumberInput.value = "";
  clearSummaryMode();
  fileInput.value = "";
  suggestionsList.innerHTML = `
    <button class="suggestion-chip" type="button">What is the objective?</button>
    <button class="suggestion-chip" type="button">What is methodology?</button>
    <button class="suggestion-chip" type="button">Conclusion details?</button>
  `;

  try {
    await fetch(`${API}/reset`, { method: "POST" });
  } catch (e) {}
});

sendBtn.addEventListener("click", askQuestion);
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") askQuestion();
});

pageNumberInput.addEventListener("keydown", async (e) => {
  if (e.key !== "Enter") return;
  e.preventDefault();

  if (selectedSummaryMode !== "page") {
    appendMessage("bot", "Click Page Info first, then type a page number and press Enter.");
    return;
  }

  const page = buildPageNumber();
  if (!page) {
    appendMessage("bot", "Please enter a valid page number and press Enter again.");
    return;
  }

  await runTool("/page-info", { page: String(page) }, `Page Info for page ${page}`);
});

summaryButtons.addEventListener("click", (e) => {
  const btn = e.target.closest(".mode-btn");
  if (!btn) return;
  handleToolButton(btn.dataset.mode);
});

toolCloseBtn.addEventListener("click", clearSummaryMode);

generateSuggestionsBtn.addEventListener("click", () => requestSuggestions(true));
generateQuizBtn.addEventListener("click", generateQuiz);
exportPdfBtn.addEventListener("click", exportChatPdf);
saveNotesBtn.addEventListener("click", saveNotes);

closeQuizBtn.addEventListener("click", () => quizModal.classList.add("hidden"));

toolsToggle.addEventListener("click", () => {
  const hidden = !smartTools.classList.contains("hidden");
  setCollapsedTools(hidden);
});

saveMemoryBtn.addEventListener("click", saveMemory);
clearMemoryBtn.addEventListener("click", clearAllMemory);
refreshMemoryBtn.addEventListener("click", loadMemory);

memoryList.addEventListener("click", (e) => {
  const edit = e.target.closest("[data-edit]");
  const del = e.target.closest("[data-delete]");

  if (edit) {
    const id = edit.getAttribute("data-edit");
    const item = (Array.from(memoryList.querySelectorAll(".memory-item")).find(row =>
      row.querySelector(`[data-edit="${id}"]`)
    ));
    const text = item ? item.querySelector(".memory-text").textContent : "";
    editingMemoryId = id;
    memoryInput.value = text;
    memoryInput.focus();
  }

  if (del) {
    const id = del.getAttribute("data-delete");
    deleteMemory(id);
  }
});

if (localStorage.getItem("smartToolsCollapsed") === "true") {
  setCollapsedTools(true);
} else {
  setCollapsedTools(false);
}

function enableInitialState() {
  enableChat();
  renderFiles();
  renderSummaryModeUI();
  loadMemory();
  requestSuggestions(false);
}

enableInitialState();