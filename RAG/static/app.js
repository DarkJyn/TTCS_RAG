/* ═══════════════════════════════════════════════════════════════
   LegalDiff — Frontend Logic
   Tab navigation, file upload, comparison, RAG chatbot
   ═══════════════════════════════════════════════════════════════ */

(() => {
  "use strict";

  // ── DOM refs ──────────────────────────────────────────────
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const statusDot = $("#status-dot");
  const statusText = $("#status-text");
  const llmDot = $("#llm-dot");
  const llmStatusText = $("#llm-status-text");
  const tabBtns = $$(".tab-btn");
  const tabPanels = $$(".tab-panel");
  const tabIndicator = $("#tab-indicator");

  // Upload
  const fileInput1 = $("#file-input-1");
  const fileInput2 = $("#file-input-2");
  const dropzone1 = $("#dropzone-1");
  const dropzone2 = $("#dropzone-2");
  const btnUpload = $("#btn-upload");
  const uploadSpinner = $("#upload-spinner");
  const uploadResult = $("#upload-result");
  const uploadResultText = $("#upload-result-text");

  // Compare
  const btnCompare = $("#btn-compare");
  const compareSpinner = $("#compare-spinner");
  const compareResults = $("#compare-results");
  const compareStats = $("#compare-stats");

  // Chat
  const chatMessages = $("#chat-messages");
  const chatInput = $("#chat-input");
  const btnSend = $("#btn-send");
  const sendIcon = $("#send-icon");
  const chatSpinner = $("#chat-spinner");

  // State
  let selectedFiles = { doc1: null, doc2: null };
  let currentFilter = "all";
  let diffData = null;
  let isChatBusy = false;

  // ── Tab Navigation ────────────────────────────────────────
  function switchTab(tabName) {
    tabBtns.forEach((btn) => btn.classList.toggle("active", btn.dataset.tab === tabName));
    tabPanels.forEach((p) => p.classList.toggle("active", p.id === `panel-${tabName}`));
    updateIndicator();
  }

  function updateIndicator() {
    const activeBtn = $(".tab-btn.active");
    if (!activeBtn) return;
    tabIndicator.style.left = activeBtn.offsetLeft + "px";
    tabIndicator.style.width = activeBtn.offsetWidth + "px";
  }

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  window.addEventListener("resize", updateIndicator);
  requestAnimationFrame(updateIndicator);

  // ── Status Check ──────────────────────────────────────────
  async function checkStatus() {
    try {
      const res = await fetch("/api/status");
      const data = await res.json();

      statusDot.className = "status-dot online";
      statusText.textContent = "Hệ thống sẵn sàng";

      if (data.ollama_available) {
        llmDot.className = "status-dot online";
        llmStatusText.textContent = `LLM: ${data.ollama_model || "available"}`;
      } else {
        llmDot.className = "status-dot offline";
        llmStatusText.textContent = "LLM chưa sẵn sàng — dùng retrieval thuần";
      }

      // Enable compare if docs loaded
      if (data.doc1_loaded && data.doc2_loaded) {
        btnCompare.disabled = false;
      }

      // Enable chat
      if (data.has_index || data.doc1_loaded) {
        btnSend.disabled = false;
      }

      return data;
    } catch {
      statusDot.className = "status-dot offline";
      statusText.textContent = "Không kết nối được server";
      llmDot.className = "status-dot offline";
      llmStatusText.textContent = "Không kết nối được server";
      return null;
    }
  }

  checkStatus();

  // ── File Upload ───────────────────────────────────────────
  function setupDropzone(dropzone, fileInput, slot) {
    const content = dropzone.querySelector(".dropzone-content");
    const loaded = dropzone.querySelector(`#loaded-${slot}`);
    const loadedName = dropzone.querySelector(`#loaded-name-${slot}`);

    // Drag events
    ["dragenter", "dragover"].forEach((ev) => {
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("drag-over");
      });
    });

    ["dragleave", "drop"].forEach((ev) => {
      dropzone.addEventListener(ev, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("drag-over");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files[0];
      if (file) selectFile(file, slot, content, loaded, loadedName, dropzone);
    });

    // Click on dropzone (but not on file-input label)
    dropzone.addEventListener("click", (e) => {
      if (e.target.classList.contains("dropzone-btn")) return;
      if (e.target === fileInput) return;
      if (e.target.classList.contains("loaded-clear")) return;
      fileInput.click();
    });

    fileInput.addEventListener("change", () => {
      const file = fileInput.files[0];
      if (file) selectFile(file, slot, content, loaded, loadedName, dropzone);
    });

    // Clear button
    const clearBtn = dropzone.querySelector(".loaded-clear");
    if (clearBtn) {
      clearBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        selectedFiles[`doc${slot}`] = null;
        content.style.display = "";
        loaded.style.display = "none";
        dropzone.classList.remove("loaded");
        fileInput.value = "";
        updateUploadBtn();
      });
    }
  }

  function selectFile(file, slot, content, loaded, loadedName, dropzone) {
    const ext = file.name.split(".").pop().toLowerCase();
    if (!["docx", "txt", "text"].includes(ext)) {
      alert("Chỉ hỗ trợ file .docx và .txt");
      return;
    }
    selectedFiles[`doc${slot}`] = file;
    content.style.display = "none";
    loaded.style.display = "flex";
    loadedName.textContent = file.name;
    dropzone.classList.add("loaded");
    updateUploadBtn();
  }

  function updateUploadBtn() {
    btnUpload.disabled = !(selectedFiles.doc1 || selectedFiles.doc2);
  }

  setupDropzone(dropzone1, fileInput1, 1);
  setupDropzone(dropzone2, fileInput2, 2);

  // Upload handler
  btnUpload.addEventListener("click", async () => {
    if (!selectedFiles.doc1 && !selectedFiles.doc2) return;

    btnUpload.disabled = true;
    uploadSpinner.style.display = "";
    uploadResult.style.display = "none";

    const formData = new FormData();
    if (selectedFiles.doc1) formData.append("doc1", selectedFiles.doc1);
    if (selectedFiles.doc2) formData.append("doc2", selectedFiles.doc2);

    try {
      const res = await fetch("/api/upload", { method: "POST", body: formData });
      const data = await res.json();

      if (data.error) {
        alert("Lỗi: " + data.error);
        return;
      }

      uploadResult.style.display = "";
      uploadResultText.textContent =
        `Đã xử lý: ${data.doc1_name || "—"} + ${data.doc2_name || "—"} | ${data.chunk_count} chunks được tạo.`;

      // Enable compare if both docs
      if (data.doc1_name && data.doc2_name) {
        btnCompare.disabled = false;
      }
      btnSend.disabled = false;

      await checkStatus();
    } catch (e) {
      alert("Lỗi kết nối: " + e.message);
    } finally {
      btnUpload.disabled = false;
      uploadSpinner.style.display = "none";
    }
  });

  // ── Compare ───────────────────────────────────────────────
  btnCompare.addEventListener("click", async () => {
    btnCompare.disabled = true;
    compareSpinner.style.display = "";

    try {
      const res = await fetch("/api/compare", { method: "POST" });
      const data = await res.json();

      if (data.error) {
        alert("Lỗi: " + data.error);
        return;
      }

      diffData = data;
      renderStats(data.stats);
      renderDiffs(data.diffs, currentFilter);
    } catch (e) {
      alert("Lỗi kết nối: " + e.message);
    } finally {
      btnCompare.disabled = false;
      compareSpinner.style.display = "none";
    }
  });

  // Filter buttons
  $$(".filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      $$(".filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentFilter = btn.dataset.filter;
      if (diffData) renderDiffs(diffData.diffs, currentFilter);
    });
  });

  function renderStats(stats) {
    compareStats.style.display = "";
    $("#stat-total").textContent = stats.total;
    $("#stat-modified").textContent = stats.modified;
    $("#stat-added").textContent = stats.added;
    $("#stat-removed").textContent = stats.removed;
    $("#stat-unchanged").textContent = stats.unchanged;
  }

  function renderDiffs(diffs, filter) {
    let filtered = filter === "all" ? diffs : diffs.filter((d) => d.diff_type === filter);

    // Sort: changes first (modified > added > removed), unchanged last
    const priority = { modified: 0, added: 1, removed: 2, unchanged: 3 };
    filtered = [...filtered].sort((a, b) => (priority[a.diff_type] ?? 9) - (priority[b.diff_type] ?? 9));

    if (filtered.length === 0) {
      compareResults.innerHTML = `<div class="empty-state"><p>Không có mục nào khớp bộ lọc "${filter}".</p></div>`;
      return;
    }

    compareResults.innerHTML = filtered.map((d, i) => buildDiffHTML(d, i)).join("");

    // Expand/collapse
    compareResults.querySelectorAll(".diff-header").forEach((header) => {
      header.addEventListener("click", () => {
        header.closest(".diff-item").classList.toggle("expanded");
      });
    });
  }

  function buildDiffHTML(d, i) {
    const heading = escHtml(d.heading || "(Phần mở đầu)");
    const sim = d.diff_type === "modified" ? `${(d.similarity * 100).toFixed(1)}% giống` : "";
    const badgeClass = d.diff_type;
    const badgeText = { added: "Thêm", removed: "Xóa", modified: "Sửa", unchanged: "Giữ nguyên" }[d.diff_type] || d.diff_type;

    let bodyHTML = "";

    if (d.diff_type === "added") {
      bodyHTML = `<div class="diff-single"><div class="diff-col-header">📗 Nội dung mới</div><div class="diff-col">${escHtml(d.new_text)}</div></div>`;
    } else if (d.diff_type === "removed") {
      bodyHTML = `<div class="diff-single"><div class="diff-col-header">📕 Nội dung bị xóa</div><div class="diff-col">${escHtml(d.old_text)}</div></div>`;
    } else if (d.diff_type === "modified") {
      const oldHighlighted = renderInlineDiff(d.inline_diffs, "old");
      const newHighlighted = renderInlineDiff(d.inline_diffs, "new");
      bodyHTML = `
        <div class="diff-columns">
          <div>
            <div class="diff-col-header">📕 Bản gốc</div>
            <div class="diff-col">${oldHighlighted}</div>
          </div>
          <div>
            <div class="diff-col-header">📗 Bản sửa đổi</div>
            <div class="diff-col">${newHighlighted}</div>
          </div>
        </div>`;
    } else {
      bodyHTML = `<div class="diff-single"><div class="diff-col-header">Nội dung (không thay đổi)</div><div class="diff-col">${escHtml(d.old_text).substring(0, 500)}${d.old_text.length > 500 ? '...' : ''}</div></div>`;
    }

    return `
      <div class="diff-item" data-type="${d.diff_type}">
        <div class="diff-header">
          <span class="diff-badge ${badgeClass}">${badgeText}</span>
          <span class="diff-heading">${heading}</span>
          <span class="diff-similarity">${sim}</span>
          <span class="diff-toggle">▼</span>
        </div>
        <div class="diff-body">${bodyHTML}</div>
      </div>`;
  }

  function renderInlineDiff(inlineDiffs, side) {
    if (!inlineDiffs || !inlineDiffs.length) return "";
    return inlineDiffs
      .map((d) => {
        const tag = d.tag;
        if (tag === "equal") {
          return escHtml(side === "old" ? d.old_text : d.new_text);
        }
        if (tag === "insert") {
          return side === "new" ? `<span class="diff-insert">${escHtml(d.new_text)}</span>` : "";
        }
        if (tag === "delete") {
          return side === "old" ? `<span class="diff-delete">${escHtml(d.old_text)}</span>` : "";
        }
        if (tag === "replace") {
          if (side === "old") return `<span class="diff-replace-old">${escHtml(d.old_text)}</span>`;
          return `<span class="diff-replace-new">${escHtml(d.new_text)}</span>`;
        }
        return escHtml(side === "old" ? d.old_text : d.new_text);
      })
      .join(" ");
  }

  // ── Chat ──────────────────────────────────────────────────
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  btnSend.addEventListener("click", sendMessage);

  // Chip quick queries
  $$(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      chatInput.value = chip.dataset.query;
      sendMessage();
    });
  });

  async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query || isChatBusy) return;

    isChatBusy = true;
    chatInput.value = "";
    sendIcon.style.display = "none";
    chatSpinner.style.display = "";

    // Remove welcome
    const welcome = chatMessages.querySelector(".chat-welcome");
    if (welcome) welcome.remove();

    // Add user message
    appendMessage("user", query);

    // Add typing indicator
    const typingId = "typing-" + Date.now();
    appendTyping(typingId);

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query }),
      });
      const data = await res.json();

      removeTyping(typingId);

      if (data.error) {
        appendMessage("bot", `⚠️ ${data.error}`, [], data);
      } else {
        appendMessage("bot", data.answer, data.citations || [], data);
      }
    } catch (e) {
      removeTyping(typingId);
      appendMessage("bot", `⚠️ Lỗi kết nối: ${e.message}`);
    } finally {
      isChatBusy = false;
      sendIcon.style.display = "";
      chatSpinner.style.display = "none";
    }
  }

  function appendMessage(role, text, citations, meta) {
    const div = document.createElement("div");
    div.className = `msg msg-${role}`;

    const avatarEmoji = role === "user" ? "👤" : "⚖️";

    let citationHTML = "";
    if (citations && citations.length > 0) {
      citationHTML = `
        <div class="citation-list">
          <div class="citation-title">📎 Nguồn trích dẫn (${citations.length})</div>
          ${citations
            .slice(0, 5)
            .map(
              (c) => `
            <div class="citation-item" onclick="this.classList.toggle('expanded')">
              <span class="cite-rank">#${c.rank}</span>
              <span class="cite-heading">${escHtml(c.heading)}</span>
              <span class="cite-score">score: ${c.score}</span>
              <br/>
              <span class="cite-source">${escHtml(shortenPath(c.source_path))}</span>
              <div class="citation-expanded">
                <div class="cite-snippet">${escHtml(c.text ? c.text.substring(0, 500) : '')}</div>
              </div>
            </div>`
            )
            .join("")}
        </div>`;
    }

    let metaTags = "";
    if (meta) {
      if (meta.evidence_status) {
        const evClass = meta.evidence_status === "SUPPORTED" ? "supported" : "insufficient";
        const evLabel = meta.evidence_status === "SUPPORTED" ? "✓ Có bằng chứng" : "⚠ Thiếu bằng chứng";
        metaTags += `<span class="evidence-tag ${evClass}">${evLabel}</span> `;
      }
      if (meta.llm_used && meta.llm_model) {
        metaTags += `<span class="llm-tag">🤖 ${escHtml(meta.llm_model)}</span>`;
      } else if (meta.llm_used === false) {
        metaTags += `<span class="llm-tag">📊 Retrieval thuần</span>`;
      }
    }

    const formattedText = role === "bot" ? formatBotText(text) : escHtml(text);

    div.innerHTML = `
      <div class="msg-avatar">${avatarEmoji}</div>
      <div class="msg-content">
        <div>${formattedText}</div>
        ${metaTags ? `<div style="margin-top:0.5rem">${metaTags}</div>` : ""}
        ${citationHTML}
      </div>`;

    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function appendTyping(id) {
    const div = document.createElement("div");
    div.className = "msg msg-bot";
    div.id = id;
    div.innerHTML = `
      <div class="msg-avatar">⚖️</div>
      <div class="msg-content">
        <div class="typing-indicator"><span></span><span></span><span></span></div>
      </div>`;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function removeTyping(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  function formatBotText(text) {
    // Simple markdown-like formatting
    let html = escHtml(text);
    // Bold **text**
    html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
    // Italic *text*
    html = html.replace(/(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g, "<em>$1</em>");
    // Line breaks
    html = html.replace(/\n/g, "<br/>");
    // Horizontal rules ---
    html = html.replace(/<br\/>---<br\/>/g, "<hr style='border-color:var(--border);margin:0.5rem 0'/>");
    return html;
  }

  function shortenPath(path) {
    if (!path) return "";
    const parts = path.replace(/\\/g, "/").split("/");
    return parts.length > 2 ? ".../" + parts.slice(-2).join("/") : path;
  }

  function escHtml(str) {
    if (!str) return "";
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }
})();
