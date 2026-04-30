(() => {
  "use strict";

  const API_BASE = (window.PROMPTFORGE_API_BASE || "/api").replace(/\/+$/, "");

  const state = {
    templates: [],
    selectedCategory: "全部",
    searchQuery: "",
    activeTemplateId: null,
    previewTemplateId: null,
    sortMode: "newest",
    providerSettings: null,
  };

  const selectors = {
    templateGrid: "#templateGrid",
    searchInput: "#searchInput",
    categoryFilterList: "#categoryFilterList",
    templateModal: "#templateModal",
    templateForm: "#templateForm",
    modalTitle: "#modalTitle",
    settingsModal: "#settingsModal",
    settingsForm: "#settingsForm",
    notificationStack: "#toastContainer",
    analyticsTemplates: "#analyticsTemplates",
    analyticsTests: "#analyticsTests",
    analyticsAvgScore: "#analyticsAvgScore",
    previewPanel: "#previewPanel",
    previewTemplateName: "#previewTemplateName",
    previewOutput: "#previewOutput",
    previewOutputTitle: "#previewOutputTitle",
    contextInput: "#contextInput",
    resultSummary: "#resultSummary",
    emptyState: "#emptyState",
    categoryCount: "#categoryCount",
  };

  const modelOptions = {
    openai: [
      "gpt-4o-mini",
      "gpt-4o",
      "gpt-4.1-mini",
      "gpt-4.1",
      "o4-mini",
    ],
    anthropic: [
      "claude-3-5-haiku-latest",
      "claude-3-5-sonnet-latest",
      "claude-3-7-sonnet-latest",
      "claude-3-opus-latest",
    ],
    custom: [
      "custom-model",
    ],
  };

  const defaultApiBases = {
    openai: "https://api.openai.com/v1",
    anthropic: "https://api.anthropic.com/v1",
    custom: "",
  };

  function qs(selector, root = document) {
    return root.querySelector(selector);
  }

  function qsa(selector, root = document) {
    return Array.from(root.querySelectorAll(selector));
  }

  function apiUrl(path) {
    const cleanPath = String(path || "").replace(/^\/+/, "");
    return `${API_BASE}/${cleanPath}`;
  }

  async function fetchAPI(path, options = {}) {
    const headers = {
      Accept: "application/json",
      ...(options.headers || {}),
    };

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const response = await fetch(apiUrl(path), {
      ...options,
      headers,
    });

    const contentType = response.headers.get("content-type") || "";
    let payload = null;

    if (contentType.includes("application/json")) {
      payload = await response.json();
    } else {
      payload = await response.text();
    }

    if (!response.ok) {
      const message =
        payload?.detail ||
        payload?.message ||
        payload?.error ||
        `请求失败，状态码：${response.status}`;
      throw new Error(message);
    }

    return payload;
  }

  function escapeHTML(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function splitComma(value) {
    return String(value || "")
      .split(/[,，]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function toArray(value) {
    if (Array.isArray(value)) {
      return value.map(String).map((item) => item.trim()).filter(Boolean);
    }

    if (typeof value === "string") {
      return splitComma(value);
    }

    return [];
  }

  function normalizeNumber(value, fallback) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
  }

  function normalizeTemplate(template) {
    return {
      id: template.id ?? template.template_id ?? template.uuid,
      name: template.name || "未命名模板",
      content: template.content || "",
      category: template.category || "未分类",
      tags: toArray(template.tags),
      variables: toArray(template.variables),
      version: template.version || "1.0",
      score: normalizeNumber(
        template.score ?? template.avg_score ?? template.average_score,
        null,
      ),
      tests: normalizeNumber(
        template.tests ?? template.test_count ?? template.evaluation_count,
        0,
      ),
      createdAt: template.created_at || template.createdAt || "",
      updatedAt:
        template.updated_at ||
        template.updatedAt ||
        template.created_at ||
        template.createdAt ||
        "",
      metadata: template.metadata || {},
    };
  }

  function getTemplatesPayload(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data?.templates)) return data.templates;
    if (Array.isArray(data?.items)) return data.items;
    if (Array.isArray(data?.results)) return data.results;
    return [];
  }

  function filteredTemplates() {
    const query = state.searchQuery.trim().toLowerCase();

    let templates = state.templates.filter((template) => {
      const matchesCategory =
        state.selectedCategory === "全部" ||
        template.category === state.selectedCategory;

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

    if (state.sortMode === "name") {
      templates = templates.sort((a, b) => a.name.localeCompare(b.name, "zh-CN"));
    } else if (state.sortMode === "score") {
      templates = templates.sort((a, b) => {
        const scoreA = typeof a.score === "number" ? a.score : -1;
        const scoreB = typeof b.score === "number" ? b.score : -1;
        return scoreB - scoreA;
      });
    } else {
      templates = templates.sort((a, b) => {
        const timeA = new Date(a.updatedAt || a.createdAt || 0).getTime();
        const timeB = new Date(b.updatedAt || b.createdAt || 0).getTime();
        return timeB - timeA;
      });
    }

    return templates;
  }

  function formatDate(value) {
    if (!value) return "未知";

    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "未知";

    return new Intl.DateTimeFormat("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).format(date);
  }

  function renderTemplateCard(template) {
    const tags = template.tags.length
      ? template.tags
          .slice(0, 5)
          .map((tag) => `<span class="tag">#${escapeHTML(tag)}</span>`)
          .join("")
      : `<span class="tag">暂无标签</span>`;

    const variables = template.variables.length
      ? template.variables
          .slice(0, 6)
          .map((variable) => `<span class="variable">{{${escapeHTML(variable)}}}</span>`)
          .join("")
      : `<span class="variable">无变量</span>`;

    const scoreText =
      typeof template.score === "number" ? `${template.score.toFixed(2)}分` : "未评分";

    return `
      <article class="template-card" data-template-id="${escapeHTML(template.id)}">
        <div class="template-top">
          <div>
            <h3 class="template-title template-name">${escapeHTML(template.name)}</h3>
            <span class="category-chip template-category">
              ${escapeHTML(template.category)} · 版本 ${escapeHTML(template.version)}
            </span>
          </div>
          <span class="score-badge">${escapeHTML(scoreText)}</span>
        </div>

        <p class="template-preview template-content-preview">
          ${escapeHTML(template.content || "暂无模板内容")}
        </p>

        <div class="tag-list tag-row">${tags}</div>
        <div class="variable-list">${variables}</div>

        <div class="template-meta">
          <span>测试：${Number(template.tests || 0)}次</span>
          <span>更新：${escapeHTML(formatDate(template.updatedAt || template.createdAt))}</span>
        </div>

        <div class="template-actions">
          <button class="btn btn-primary icon-btn" type="button" data-action="run" data-id="${escapeHTML(template.id)}" aria-label="运行模型">
            运行模型
          </button>
          <button class="btn btn-secondary icon-btn" type="button" data-action="preview" data-id="${escapeHTML(template.id)}" aria-label="预览模板">
            预览渲染
          </button>
          <button class="btn btn-secondary icon-btn" type="button" data-action="evaluate" data-id="${escapeHTML(template.id)}" aria-label="评估模板">
            一键评估
          </button>
          <button class="btn btn-secondary icon-btn" type="button" data-action="edit" data-id="${escapeHTML(template.id)}" aria-label="编辑模板">
            编辑模板
          </button>
          <button class="btn btn-danger icon-btn" type="button" data-action="delete" data-id="${escapeHTML(template.id)}" aria-label="删除模板">
            删除模板
          </button>
        </div>
      </article>
    `;
  }

  function renderTemplateGrid() {
    const grid = qs(selectors.templateGrid);
    if (!grid) return;

    const templates = filteredTemplates();

    const summary = qs(selectors.resultSummary);
    if (summary) {
      summary.textContent = `共 ${templates.length} 个模板，筛选自 ${state.templates.length} 个模板`;
    }

    const emptyState = qs(selectors.emptyState);
    if (emptyState) {
      emptyState.classList.toggle("hidden", templates.length > 0);
    }

    if (templates.length === 0) {
      grid.innerHTML = "";
      return;
    }

    grid.innerHTML = templates.map(renderTemplateCard).join("");
  }

  function renderCategories() {
    const container = qs(selectors.categoryFilterList);
    if (!container) return;

    const counts = new Map();
    counts.set("全部", state.templates.length);

    state.templates.forEach((template) => {
      const category = template.category || "未分类";
      counts.set(category, (counts.get(category) || 0) + 1);
    });

    const categories = Array.from(counts.entries());

    container.innerHTML = categories
      .map(([category, count]) => {
        const active = category === state.selectedCategory ? "active" : "";

        return `
          <button class="category-item ${active}" type="button" data-category-filter="${escapeHTML(category)}">
            <span class="category-name">${escapeHTML(category === "全部" ? "全部模板" : category)}</span>
            <span class="category-number">${count}</span>
          </button>
        `;
      })
      .join("");

    const badge = qs(selectors.categoryCount);
    if (badge) {
      badge.textContent = String(Math.max(categories.length - 1, 0));
    }
  }

  function renderAnalytics(analytics = {}) {
    const templateCount =
      analytics.templates_count ??
      analytics.template_count ??
      analytics.total_templates ??
      analytics.templates ??
      state.templates.length;

    const testCount =
      analytics.test_results_count ??
      analytics.test_count ??
      analytics.total_tests ??
      analytics.tests ??
      0;

    const avgScore =
      analytics.average_score ??
      analytics.avg_score ??
      analytics.averageScore ??
      0;

    const templateEl = qs(selectors.analyticsTemplates);
    const testsEl = qs(selectors.analyticsTests);
    const avgEl = qs(selectors.analyticsAvgScore);

    if (templateEl) templateEl.textContent = String(templateCount);
    if (testsEl) testsEl.textContent = String(testCount);
    if (avgEl) avgEl.textContent = Number(avgScore || 0).toFixed(2);
  }

  async function loadTemplates() {
    try {
      const data = await fetchAPI("templates/");
      state.templates = getTemplatesPayload(data).map(normalizeTemplate);

      renderCategories();
      renderTemplateGrid();
      await loadAnalytics();
    } catch (error) {
      showNotification(`模板加载失败：${error.message}`, "error");
    }
  }

  async function loadAnalytics() {
    try {
      const analytics = await fetchAPI("analytics/");
      renderAnalytics(analytics);
    } catch {
      renderAnalytics({
        templates_count: state.templates.length,
        test_results_count: state.templates.reduce(
          (sum, template) => sum + Number(template.tests || 0),
          0,
        ),
        average_score: 0,
      });
    }
  }

  async function loadProviderSettings() {
    try {
      const settings = await fetchAPI("settings/provider");
      state.providerSettings = settings;
      fillSettingsForm(settings);
    } catch {
      state.providerSettings = null;
    }
  }

  function fillSettingsForm(settings) {
    const form = qs(selectors.settingsForm);
    if (!form) return;

    const provider = settings?.provider || "openai";
    const model = settings?.model || modelOptions[provider]?.[0] || "gpt-4o-mini";

    form.elements.provider.value = provider;
    refreshModelOptions(provider, model);

    form.elements.api_base.value =
      settings?.api_base || defaultApiBases[provider] || "";

    form.elements.api_key.value = "";

    const hint = qs("#savedApiKeyHint");
    if (hint) {
      hint.textContent = settings?.configured
        ? `已保存密钥：${settings.api_key}`
        : "尚未保存密钥";
    }
  }

  function refreshModelOptions(provider, selectedModel = "") {
    const select = qs("#providerModel");
    if (!select) return;

    const options = modelOptions[provider] || modelOptions.openai;
    const values = selectedModel && !options.includes(selectedModel)
      ? [selectedModel, ...options]
      : options;

    select.innerHTML = values
      .map((model) => {
        const selected = model === selectedModel ? "selected" : "";
        return `<option value="${escapeHTML(model)}" ${selected}>${escapeHTML(model)}</option>`;
      })
      .join("");
  }

  function openTemplateModal(template = null) {
    const modal = qs(selectors.templateModal);
    const form = qs(selectors.templateForm);
    const title = qs(selectors.modalTitle);

    if (!modal || !form) return;

    state.activeTemplateId = template?.id ?? null;

    if (title) {
      title.textContent = template ? "编辑模板" : "新建模板";
    }

    form.reset();

    form.elements.name.value = template?.name || "";
    form.elements.category.value = template?.category || "";
    form.elements.version.value = template?.version || "1.0";
    form.elements.tags.value = template?.tags?.join(", ") || "";
    form.elements.variables.value = template?.variables?.join(", ") || "";
    form.elements.content.value = template?.content || "";

    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");

    setTimeout(() => {
      form.elements.name?.focus();
    }, 50);
  }

  function closeTemplateModal() {
    const modal = qs(selectors.templateModal);
    const form = qs(selectors.templateForm);

    if (!modal || !form) return;

    state.activeTemplateId = null;
    form.reset();
    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
  }

  async function openSettingsModal() {
    const modal = qs(selectors.settingsModal);
    if (!modal) return;

    modal.classList.remove("hidden");
    modal.setAttribute("aria-hidden", "false");

    if (!state.providerSettings) {
      await loadProviderSettings();
    }

    setTimeout(() => {
      qs("#providerSelect")?.focus();
    }, 50);
  }

  function closeSettingsModal() {
    const modal = qs(selectors.settingsModal);
    if (!modal) return;

    modal.classList.add("hidden");
    modal.setAttribute("aria-hidden", "true");
  }

  function getTemplatePayload(form) {
    return {
      name: form.elements.name.value.trim(),
      content: form.elements.content.value.trim(),
      category: form.elements.category.value.trim() || "未分类",
      tags: splitComma(form.elements.tags.value),
      variables: splitComma(form.elements.variables.value),
      version: form.elements.version.value.trim() || "1.0",
      metadata: {},
    };
  }

  async function saveTemplate(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const payload = getTemplatePayload(form);

    if (!payload.name || !payload.content) {
      showNotification("模板名称和内容不能为空", "warning");
      return;
    }

    const submitButton = form.querySelector('[type="submit"]');
    setButtonBusy(submitButton, true, "保存中");

    try {
      if (state.activeTemplateId) {
        await fetchAPI(`templates/${encodeURIComponent(state.activeTemplateId)}`, {
          method: "PUT",
          body: JSON.stringify(payload),
        });
        showNotification("模板已更新", "success");
      } else {
        await fetchAPI("templates/", {
          method: "POST",
          body: JSON.stringify(payload),
        });
        showNotification("模板已创建", "success");
      }

      closeTemplateModal();
      await loadTemplates();
    } catch (error) {
      showNotification(`保存失败：${error.message}`, "error");
    } finally {
      setButtonBusy(submitButton, false);
    }
  }

  function getSettingsPayload(form) {
    const payload = {
      provider: form.elements.provider.value,
      model: form.elements.model.value.trim(),
      api_base: form.elements.api_base.value.trim(),
    };

    const apiKey = form.elements.api_key.value.trim();
    if (apiKey) {
      payload.api_key = apiKey;
    }

    return payload;
  }

  async function saveProviderSettings(event) {
    event.preventDefault();

    const form = event.currentTarget;
    const payload = getSettingsPayload(form);

    if (!payload.model) {
      showNotification("请选择模型", "warning");
      return;
    }

    if (payload.provider === "custom" && !payload.api_base) {
      showNotification("自定义接口需要填写 API 地址", "warning");
      return;
    }

    const submitButton = form.querySelector('[type="submit"]');
    setButtonBusy(submitButton, true, "保存中");

    try {
      const settings = await fetchAPI("settings/provider", {
        method: "POST",
        body: JSON.stringify(payload),
      });

      state.providerSettings = settings;
      fillSettingsForm(settings);
      closeSettingsModal();
      showNotification("模型设置已保存", "success");
    } catch (error) {
      showNotification(`设置保存失败：${error.message}`, "error");
    } finally {
      setButtonBusy(submitButton, false);
    }
  }

  async function deleteTemplate(templateId) {
    const template = state.templates.find((item) => String(item.id) === String(templateId));

    if (!template) {
      showNotification("没有找到要删除的模板", "error");
      return;
    }

    const shouldDelete = window.confirm(`确定要删除“${template.name}”吗？此操作无法撤销。`);
    if (!shouldDelete) return;

    try {
      await fetchAPI(`templates/${encodeURIComponent(templateId)}`, {
        method: "DELETE",
      });

      showNotification("模板已删除", "success");

      if (String(state.previewTemplateId) === String(templateId)) {
        closePreviewPanel();
      }

      await loadTemplates();
    } catch (error) {
      showNotification(`删除失败：${error.message}`, "error");
    }
  }

  function openPreviewPanel(templateId) {
    const template = state.templates.find((item) => String(item.id) === String(templateId));

    if (!template) {
      showNotification("没有找到要预览的模板", "error");
      return null;
    }

    state.previewTemplateId = template.id;
    state.activeTemplateId = template.id;

    const panel = qs(selectors.previewPanel);
    const nameEl = qs(selectors.previewTemplateName);
    const output = qs(selectors.previewOutput);
    const outputTitle = qs(selectors.previewOutputTitle);
    const contextInput = qs(selectors.contextInput);

    if (nameEl) {
      nameEl.textContent = `当前模板：${template.name}`;
    }

    if (outputTitle) {
      outputTitle.textContent = "输出结果";
    }

    if (contextInput) {
      const defaultContext = Object.fromEntries(
        (template.variables || []).map((variable) => [variable, ""]),
      );
      contextInput.value = JSON.stringify(defaultContext, null, 2);
    }

    if (output) {
      output.textContent = template.content || "暂无预览内容";
    }

    panel?.classList.remove("hidden");
    panel?.scrollIntoView({ behavior: "smooth", block: "start" });

    return template;
  }

  function closePreviewPanel() {
    qs(selectors.previewPanel)?.classList.add("hidden");

    const output = qs(selectors.previewOutput);
    const contextInput = qs(selectors.contextInput);

    if (output) output.textContent = "暂无预览内容";
    if (contextInput) contextInput.value = "";

    state.previewTemplateId = null;
  }

  function parseContextInput() {
    const input = qs(selectors.contextInput);
    const raw = input?.value?.trim() || "";

    if (!raw) return {};

    const parsed = JSON.parse(raw);

    if (!parsed || Array.isArray(parsed) || typeof parsed !== "object") {
      throw new Error("变量上下文必须是对象");
    }

    return parsed;
  }

  function renderLocally(template, context) {
    return template.content.replace(/\{\{\s*([^}]+?)\s*\}\}/g, (_, key) => {
      const cleanKey = String(key).trim();
      const value = context[cleanKey];

      if (value === undefined || value === null || value === "") {
        return `{{${cleanKey}}}`;
      }

      return String(value);
    });
  }

  async function renderPreview(templateId = state.previewTemplateId) {
    const template = state.templates.find((item) => String(item.id) === String(templateId));

    if (!template) {
      showNotification("请先选择要预览的模板", "warning");
      return null;
    }

    let context = {};

    try {
      context = parseContextInput();
    } catch {
      showNotification("变量上下文必须是有效的对象格式", "error");
      return null;
    }

    const output = qs(selectors.previewOutput);
    const outputTitle = qs(selectors.previewOutputTitle);
    const button = qs("#renderPreviewButton");

    if (outputTitle) {
      outputTitle.textContent = "渲染预览";
    }

    setButtonBusy(button, true, "生成中");

    try {
      const response = await fetchAPI("render/", {
        method: "POST",
        body: JSON.stringify({
          template_id: Number(template.id),
          context,
        }),
      });

      const rendered =
        response?.rendered ??
        response?.output ??
        response?.content ??
        response?.result ??
        "";

      if (output) {
        output.textContent = rendered || "后端没有返回预览内容";
      }

      showNotification("预览已生成", "success");
      return rendered;
    } catch (error) {
      const fallback = renderLocally(template, context);

      if (output) {
        output.textContent = fallback;
      }

      showNotification(`后端渲染失败，已使用本地预览：${error.message}`, "warning");
      return fallback;
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function runTemplateWithAI(templateId = state.previewTemplateId) {
    const template = state.templates.find((item) => String(item.id) === String(templateId));

    if (!template) {
      showNotification("请先选择要运行的模板", "warning");
      return null;
    }

    state.previewTemplateId = template.id;
    state.activeTemplateId = template.id;

    let context = {};

    try {
      context = parseContextInput();
    } catch {
      showNotification("变量上下文必须是有效的对象格式", "error");
      return null;
    }

    const output = qs(selectors.previewOutput);
    const outputTitle = qs(selectors.previewOutputTitle);
    const button = qs("#runChatButton");

    if (outputTitle) {
      outputTitle.textContent = "模型回复";
    }

    if (output) {
      output.textContent = "模型正在生成回复，请稍候……";
    }

    setButtonBusy(button, true, "运行中");

    try {
      const response = await fetchAPI("chat/", {
        method: "POST",
        body: JSON.stringify({
          template_id: Number(template.id),
          context,
        }),
      });

      const aiText =
        response?.response ??
        response?.ai_response ??
        response?.output ??
        response?.result ??
        "";

      if (output) {
        output.textContent = aiText || "模型没有返回内容";
      }

      const latency = Number(response?.latency_ms || 0);
      const model = response?.model ? `，模型：${response.model}` : "";
      const speed = latency ? `，耗时：${latency}毫秒` : "";

      showNotification(`运行完成${model}${speed}`, "success");
      await loadAnalytics();

      return response;
    } catch (error) {
      if (output) {
        output.textContent = `运行失败：${error.message}`;
      }

      showNotification(`运行失败：${error.message}`, "error");
      return null;
    } finally {
      setButtonBusy(button, false);
    }
  }

  async function runTemplateFromCard(templateId) {
    const template = openPreviewPanel(templateId);
    if (!template) return;

    await runTemplateWithAI(template.id);
  }

  async function evaluatePrompt(templateId) {
    const template = state.templates.find((item) => String(item.id) === String(templateId));

    if (!template) {
      showNotification("没有找到要评估的模板", "error");
      return null;
    }

    const defaultInput = Object.fromEntries(
      (template.variables || []).map((variable) => [variable, `{${variable}}`]),
    );

    try {
      const result = await fetchAPI("evaluate/", {
        method: "POST",
        body: JSON.stringify({
          template_id: Number(template.id),
          input_data: defaultInput,
          model_name: "本地评估",
        }),
      });

      const score = result?.score ?? result?.result?.score;
      const message =
        typeof score === "number"
          ? `评估完成，得分：${score.toFixed(2)}`
          : "评估完成，结果已更新";

      showNotification(message, "success");
      await loadAnalytics();
      await loadTemplates();

      return result;
    } catch (error) {
      showNotification(`评估失败：${error.message}`, "error");
      return null;
    }
  }

  function searchTemplates(query) {
    state.searchQuery = query || "";
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

    const titleMap = {
      success: "成功",
      error: "错误",
      warning: "提示",
      info: "消息",
    };

    toast.innerHTML = `
      <p class="toast-title">${escapeHTML(titleMap[type] || "消息")}</p>
      <p class="toast-message">${escapeHTML(message)}</p>
    `;

    container.appendChild(toast);

    window.setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(24px)";
      window.setTimeout(() => toast.remove(), 200);
    }, timeout);
  }

  function setButtonBusy(button, busy, text = "处理中") {
    if (!button) return;

    if (busy) {
      button.dataset.originalText = button.textContent;
      button.textContent = text;
      button.disabled = true;
    } else {
      button.textContent = button.dataset.originalText || button.textContent;
      button.disabled = false;
      delete button.dataset.originalText;
    }
  }

  function bindEvents() {
    qs("#createTemplateButton")?.addEventListener("click", () => openTemplateModal());
    qs("#emptyCreateButton")?.addEventListener("click", () => openTemplateModal());
    qs("#refreshButton")?.addEventListener("click", loadTemplates);
    qs("#settingsButton")?.addEventListener("click", openSettingsModal);
    qs("#guideButton")?.addEventListener("click", () => {
      qs("#guideModal")?.classList.remove("hidden");
    });

    qs("#closeModalButton")?.addEventListener("click", closeTemplateModal);
    qs("#cancelModalButton")?.addEventListener("click", closeTemplateModal);
    qs(selectors.templateForm)?.addEventListener("submit", saveTemplate);

    qs("#closeSettingsModalButton")?.addEventListener("click", closeSettingsModal);
    qs("#cancelSettingsModalButton")?.addEventListener("click", closeSettingsModal);
    qs(selectors.settingsForm)?.addEventListener("submit", saveProviderSettings);

    qs("#closeGuideButton")?.addEventListener("click", () => {
      qs("#guideModal")?.classList.add("hidden");
    });
    qs("#closeGuideFooterButton")?.addEventListener("click", () => {
      qs("#guideModal")?.classList.add("hidden");
    });

    qs("#providerSelect")?.addEventListener("change", (event) => {
      const provider = event.target.value;
      refreshModelOptions(provider, modelOptions[provider]?.[0] || "");

      const apiBaseInput = qs("#providerApiBase");
      if (apiBaseInput) {
        apiBaseInput.value = defaultApiBases[provider] || "";
      }
    });

    qs(selectors.searchInput)?.addEventListener("input", (event) => {
      searchTemplates(event.target.value);
    });

    qs("#sortSelect")?.addEventListener("change", (event) => {
      state.sortMode = event.target.value;
      renderTemplateGrid();
    });

    qs("#closePreviewButton")?.addEventListener("click", closePreviewPanel);

    qs("#renderPreviewButton")?.addEventListener("click", () => {
      renderPreview(state.previewTemplateId);
    });

    qs("#runChatButton")?.addEventListener("click", () => {
      runTemplateWithAI(state.previewTemplateId);
    });

    qs("#clearContextButton")?.addEventListener("click", () => {
      const input = qs(selectors.contextInput);
      if (input) input.value = "";

      const output = qs(selectors.previewOutput);
      if (output) output.textContent = "暂无预览内容";
    });

    qs("#copyPreviewButton")?.addEventListener("click", async () => {
      const text = qs(selectors.previewOutput)?.textContent?.trim();

      if (!text || text === "暂无预览内容") {
        showNotification("当前没有可复制的内容", "warning");
        return;
      }

      try {
        await navigator.clipboard.writeText(text);
        showNotification("内容已复制", "success");
      } catch {
        showNotification("复制失败，请手动选择文本复制", "error");
      }
    });

    qs(selectors.templateModal)?.addEventListener("click", (event) => {
      if (
        event.target.matches(selectors.templateModal) ||
        event.target.classList.contains("modal-backdrop")
      ) {
        closeTemplateModal();
      }
    });

    qs(selectors.settingsModal)?.addEventListener("click", (event) => {
      if (
        event.target.matches(selectors.settingsModal) ||
        event.target.classList.contains("modal-backdrop")
      ) {
        closeSettingsModal();
      }
    });

    document.addEventListener("click", (event) => {
      const filter = event.target.closest("[data-category-filter]");
      if (filter) {
        state.selectedCategory = filter.dataset.categoryFilter || "全部";
        renderCategories();
        renderTemplateGrid();
        return;
      }

      const actionButton = event.target.closest("[data-action]");
      if (!actionButton) return;

      const { action, id } = actionButton.dataset;

      if (action === "run") {
        runTemplateFromCard(id);
        return;
      }

      if (action === "preview") {
        openPreviewPanel(id);
        return;
      }

      if (action === "evaluate") {
        evaluatePrompt(id);
        return;
      }

      if (action === "edit") {
        const template = state.templates.find((item) => String(item.id) === String(id));
        openTemplateModal(template);
        return;
      }

      if (action === "delete") {
        deleteTemplate(id);
      }
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeTemplateModal();
        closeSettingsModal();
        closePreviewPanel();
      }
    });
  }

  document.addEventListener("DOMContentLoaded", () => {
    bindEvents();
    refreshModelOptions("openai", "gpt-4o-mini");
    loadProviderSettings();
    loadTemplates();
  });
})();

还需要确认你的依赖里有 httpx；没有的话加到依赖文件中，例如：

httpx>=0.27.0