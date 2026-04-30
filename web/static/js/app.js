const API_BASE = window.PROMPTFORGE_API_BASE || "";
const state = {
  templates: [],
  selectedCategory: "all",
  searchQuery: "",
  activeTemplateId: null,
};

const selectors = {
  templateGrid: "#templateGrid",
  searchInput: "#searchInput",
  categoryFilters: "[data-category-filter]",
  templateModal: "#templateModal",
  templateForm: "#templateForm",
  modalTitle: "#modalTitle",
  notificationStack: "#toastContainer",
  analyticsTemplates: "#analyticsTemplates",
  analyticsTests: "#analyticsTests",
  analyticsAvgScore: "#analyticsAvgScore",
  previewOutput: "#previewOutput",
};

async function fetchAPI(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    Accept: "application/json",
    ...(options.headers || {}),
  };

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let payload = null;
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    payload = await response.text();
  }

  if (!response.ok) {
    const message =
      payload?.detail ||
      payload?.message ||
      `Request failed with status ${response.status}`;
    throw new Error(message);
  }

  return payload;
}

function qs(selector, root = document) {
  return root.querySelector(selector);
}

function qsa(selector, root = document) {
  return Array.from(root.querySelectorAll(selector));
}

function escapeHTML(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function normalizeTemplate(template) {
  return {
    id: template.id,
    name: template.name || "Untitled Prompt",
    content: template.content || "",
    category: template.category || "General",
    tags: Array.isArray(template.tags)
      ? template.tags
      : String(template.tags || "")
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
    variables: Array.isArray(template.variables)
      ? template.variables
      : String(template.variables || "")
          .split(",")
          .map((variable) => variable.trim())
          .filter(Boolean),
    version: template.version || "1.0.0",
    metadata: template.metadata || {},
  };
}

function filteredTemplates() {
  return state.templates.filter((template) => {
    const matchesCategory =
      state.selectedCategory === "all" ||
      template.category.toLowerCase() === state.selectedCategory.toLowerCase();

    const query = state.searchQuery.trim().toLowerCase();
    const searchable = [
      template.name,
      template.content,
      template.category,
      template.tags.join(" "),
      template.variables.join(" "),
    ]
      .join(" ")
      .toLowerCase();

    return matchesCategory && (!query || searchable.includes(query));
  });
}

function renderTemplateCard(template) {
  const tags = template.tags
    .slice(0, 4)
    .map((tag) => `<span class="tag-badge">#${escapeHTML(tag)}</span>`)
    .join("");

  return `
    <article class="template-card" data-template-id="${template.id}">
      <div class="template-card-header">
        <h3 class="template-name">${escapeHTML(template.name)}</h3>
        <p class="template-category">${escapeHTML(template.category)} · v${escapeHTML(template.version)}</p>
      </div>

      <p class="template-content-preview">${escapeHTML(template.content)}</p>

      <div class="template-card-footer">
        <div class="tag-row">${tags}</div>
        <div class="template-actions">
          <button class="icon-btn" type="button" data-action="preview" data-id="${template.id}" aria-label="Preview template">▶</button>
          <button class="icon-btn" type="button" data-action="edit" data-id="${template.id}" aria-label="Edit template">✎</button>
          <button class="icon-btn" type="button" data-action="evaluate" data-id="${template.id}" aria-label="Evaluate template">◎</button>
          <button class="icon-btn" type="button" data-action="delete" data-id="${template.id}" aria-label="Delete template">×</button>
        </div>
      </div>
    </article>
  `;
}

function renderTemplateGrid() {
  const grid = qs(selectors.templateGrid);
  if (!grid) return;

  const templates = filteredTemplates();

  // Update result summary
  const summary = qs("#resultSummary");
  if (summary) {
    summary.textContent = `共 ${templates.length} 个模板，筛选自 ${state.templates.length} 个`;
  }

  // Toggle empty state
  qs("#emptyState")?.classList.toggle("hidden", templates.length > 0);

  const templates = filteredTemplates();

  if (templates.length === 0) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-illustration">✦</div>
        <h3>暂无模板</h3>
        <p>创建一个提示词模板或调整筛选条件。</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = templates.map(renderTemplateCard).join("");
}

function renderCategories() {
  const categories = new Set(state.templates.map((template) => template.category));
  const container = qs("#categoryFilterList");
  if (!container) return;

  const categoryButtons = Array.from(categories)
    .sort((a, b) => a.localeCompare(b))
    .map(
      (category) => `
        <button class="category-item" type="button" data-category-filter="${escapeHTML(category)}">
          <span class="category-name">${escapeHTML(category)}</span>
          <span class="category-number">${state.templates.filter((t) => t.category === category).length}</span>
        </button>
      `,
    )
    .join("");

  container.innerHTML = `
    <button class="category-item active" type="button" data-category-filter="all">
      <span class="category-name">全部模板</span>
      <span class="category-number">${state.templates.length}</span>
    </button>
    ${categoryButtons}
  `;

  const badge = qs("#categoryCount");
  if (badge) badge.textContent = categories.size;
}

async function loadTemplates() {
  try {
    const templates = await fetchAPI("/templates/");
    state.templates = templates.map(normalizeTemplate);
    renderCategories();
    renderTemplateGrid();
    await loadAnalytics();
  } catch (error) {
    showNotification(error.message, "error");
  }
}

async function loadAnalytics() {
  try {
    const analytics = await fetchAPI("/analytics/");
    const templateCount = analytics.templates_count ?? state.templates.length;
    const testCount = analytics.test_results_count ?? 0;
    const avgScore = analytics.average_score ?? analytics.avg_score ?? 0;

    if (qs(selectors.analyticsTemplates)) {
      qs(selectors.analyticsTemplates).textContent = templateCount;
    }

    if (qs(selectors.analyticsTests)) {
      qs(selectors.analyticsTests).textContent = testCount;
    }

    if (qs(selectors.analyticsAvgScore)) {
      qs(selectors.analyticsAvgScore).textContent = Number(avgScore).toFixed(2);
    }
  } catch {
    if (qs(selectors.analyticsTemplates)) {
      qs(selectors.analyticsTemplates).textContent = state.templates.length;
    }
  }
}

function openTemplateModal(template = null) {
  const modal = qs(selectors.templateModal);
  const form = qs(selectors.templateForm);

  if (!modal || !form) return;

  state.activeTemplateId = template?.id ?? null;

  qs(selectors.modalTitle).textContent = template ? "编辑模板" : "新建模板";
  form.elements.name.value = template?.name || "";
  form.elements.category.value = template?.category || "";
  form.elements.version.value = template?.version || "1.0.0";
  form.elements.tags.value = template?.tags?.join(", ") || "";
  form.elements.variables.value = template?.variables?.join(", ") || "";
  form.elements.content.value = template?.content || "";

  modal.classList.add("is-open");
  form.elements.name.focus();
}

function closeTemplateModal() {
  const modal = qs(selectors.templateModal);
  const form = qs(selectors.templateForm);

  if (!modal || !form) return;

  state.activeTemplateId = null;
  form.reset();
  modal.classList.remove("is-open");
}

async function createTemplate(event) {
  event.preventDefault();

  const form = event.currentTarget;
  const now = new Date().toISOString();

  const payload = {
    id: state.activeTemplateId || 0,
    name: form.elements.name.value.trim(),
    content: form.elements.content.value,
    category: form.elements.category.value.trim() || "General",
    tags: form.elements.tags.value
      .split(",")
      .map((tag) => tag.trim())
      .filter(Boolean),
    variables: form.elements.variables.value
      .split(",")
      .map((variable) => variable.trim())
      .filter(Boolean),
    version: form.elements.version.value.trim() || "1.0.0",
    created_at: now,
    updated_at: now,
    metadata: {},
  };

  if (!payload.name || !payload.content) {
    showNotification("模板名称和内容不能为空", "warning");
    return;
  }

  try {
    await fetchAPI("/templates/", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    showNotification("模板已保存", "success");
    closeTemplateModal();
    await loadTemplates();
  } catch (error) {
    showNotification(error.message, "error");
  }
}

async function deleteTemplate(templateId) {
  const template = state.templates.find((item) => Number(item.id) === Number(templateId));

  if (!template) {
    showNotification("Template not found.", "error");
    return;
  }

  const shouldDelete = window.confirm(`确定要删除"${template.name}"吗？`);
  if (!shouldDelete) return;

  try {
    await fetchAPI(`/templates/${templateId}`, { method: "DELETE" });
    showNotification("模板已删除", "success");
    await loadTemplates();
  } catch (error) {
    showNotification(error.message, "error");
  }
}

async function renderPreview(templateId, context = {}) {
  const template = state.templates.find((item) => Number(item.id) === Number(templateId));
  if (!template) {
    showNotification("模板未找到", "error");
    return null;
  }

  state.activeTemplateId = templateId;
  const defaultContext = Object.fromEntries(
    (template.variables || []).map((variable) => [variable, `{${variable}}`]),
  );

  // Update preview panel UI
  const nameEl = qs("#previewTemplateName");
  if (nameEl) nameEl.textContent = template.name;

  // Update context input with variable hints
  const ctxInput = qs("#contextInput");
  if (ctxInput && Object.keys(context).length === 0) {
    ctxInput.value = JSON.stringify(defaultContext, null, 2);
  }

  try {
    const response = await fetchAPI(
      `/render/`,
      {
        method: "POST",
        body: JSON.stringify({ template_id: templateId, context: { ...defaultContext, ...context } }),
      },
    );

    const rendered = response.rendered ?? response.output ?? String(response);
    const output = qs(selectors.previewOutput);

    if (output) {
      output.textContent = rendered;
    }

    qs("#previewPanel")?.classList.remove("hidden");
    showNotification("预览已生成", "success");
    return rendered;
  } catch (error) {
    showNotification(error.message, "error");
    return null;
  }
}

async function evaluatePrompt(templateId, inputData = {}, modelName = "local-preview") {
  const template = state.templates.find((item) => Number(item.id) === Number(templateId));
  const defaultInput = Object.fromEntries(
    (template?.variables || []).map((variable) => [variable, `{${variable}}`]),
  );

  try {
    const query = new URLSearchParams({
      template_id: templateId,
      model_name: modelName,
    });

    const result = await fetchAPI(`/evaluate/?${query.toString()}`, {
      method: "POST",
      body: JSON.stringify({ ...defaultInput, ...inputData }),
    });

    showNotification(`评估完成。得分: ${result.score ?? "N/A"}`, "success");
    await loadAnalytics();
    return result;
  } catch (error) {
    showNotification(error.message, "error");
    return null;
  }
}

async function searchTemplates(query) {
  state.searchQuery = query;

  try {
    if (query.trim().length >= 2) {
      const searchResults = await fetchAPI(`/templates/?search=${encodeURIComponent(query)}`).catch(
        () => null,
      );

      if (Array.isArray(searchResults)) {
        state.templates = searchResults.map(normalizeTemplate);
      }
    } else {
      await loadTemplates();
      return;
    }
  } catch {
    // Client-side filtering remains available when the API does not expose search.
  }

  renderTemplateGrid();
}

function showNotification(message, type = "info", timeout = 4200) {
  let container = qs(selectors.notificationStack);

  if (!container) {
    container = document.createElement("div");
    container.id = "toastContainer";
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.textContent = message;

  container.appendChild(toast);

  window.setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateX(24px)";
    window.setTimeout(() => toast.remove(), 180);
  }, timeout);
}

function bindEvents() {
  qs("#createTemplateButton")?.addEventListener("click", () => openTemplateModal());
  qs("#closeModalButton")?.addEventListener("click", closeTemplateModal);
  qs("#cancelModalButton")?.addEventListener("click", closeTemplateModal);
  qs(selectors.templateForm)?.addEventListener("submit", createTemplate);

  qs(selectors.searchInput)?.addEventListener("input", (event) => {
    searchTemplates(event.target.value);
  });

  document.addEventListener("click", (event) => {
    const filter = event.target.closest("[data-category-filter]");
    if (filter) {
      state.selectedCategory = filter.dataset.categoryFilter;
      qsa("[data-category-filter]").forEach((button) => {
        button.classList.toggle("active", button === filter);
      });
      renderTemplateGrid();
      return;
    }

    const actionButton = event.target.closest("[data-action]");
    if (!actionButton) return;

    const { action, id } = actionButton.dataset;

    if (action === "delete") {
      deleteTemplate(id);
    }

    if (action === "preview") {
      renderPreview(id);
    }

    if (action === "evaluate") {
      evaluatePrompt(id);
    }

    if (action === "edit") {
      const template = state.templates.find((item) => Number(item.id) === Number(id));
      openTemplateModal(template);
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      closeTemplateModal();
    }
  });

  qs(selectors.templateModal)?.addEventListener("click", (event) => {
    if (event.target.matches(selectors.templateModal)) {
      closeTemplateModal();
    }
  });

  // New UI handlers
  qs("#refreshButton")?.addEventListener("click", loadTemplates);
  qs("#emptyCreateButton")?.addEventListener("click", () => openTemplateModal());
  qs("#closePreviewButton")?.addEventListener("click", () => {
    qs("#previewPanel")?.classList.add("hidden");
  });
  qs("#renderPreviewButton")?.addEventListener("click", async () => {
    const templateId = state.activeTemplateId;
    if (!templateId) return showNotification("请先点击模板的预览按钮", "warning");
    try {
      const contextText = qs("#contextInput")?.value;
      let context = {};
      if (contextText) {
        try { context = JSON.parse(contextText); }
        catch { showNotification("JSON 格式错误", "error"); return; }
      }
      await renderPreview(templateId, context);
    } catch (e) { showNotification(e.message, "error"); }
  });
  qs("#clearContextButton")?.addEventListener("click", () => {
    qs("#contextInput").value = "";
  });
  qs("#copyPreviewButton")?.addEventListener("click", () => {
    const text = qs("#previewOutput")?.textContent;
    if (text && text !== "暂无预览内容") {
      navigator.clipboard.writeText(text).then(() => showNotification("已复制到剪贴板", "success"));
    }
  });
  qs("#sortSelect")?.addEventListener("change", (event) => {
    const sort = event.target.value;
    state.templates.sort((a, b) => {
      if (sort === "name") return a.name.localeCompare(b.name);
      return new Date(b.updated_at) - new Date(a.updated_at);
    });
    renderTemplateGrid();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadTemplates();
});
