(() => {
  const course = readJsonScript("ka-course-payload");
  const runtimeOptions = readJsonScript("ka-runtime-options") || {};
  const prompts = readJsonScript("ka-mentor-prompts") || {};
  const encryptedProfile = readJsonScript("ka-encrypted-profile");

  if (!course) {
    return;
  }

  const state = {
    connection: null,
    connectionMode: null,
    questions: [],
    assessment: null,
    chatHistory: [],
  };

  const relayUrl = String(runtimeOptions.relay_url || "http://127.0.0.1:8760").replace(/\/+$/, "");

  const ui = {
    classroom: document.getElementById("mentor-classroom"),
    sidebarToggle: document.getElementById("mentor-sidebar-toggle"),
    sidebarClose: document.getElementById("mentor-sidebar-close"),
    sidebarBackdrop: document.getElementById("mentor-sidebar-backdrop"),
    intro: document.getElementById("mentor-classroom-intro"),
    manualCard: document.getElementById("mentor-manual-card"),
    injectedCard: document.getElementById("mentor-injected-card"),
    baseUrlInput: document.getElementById("mentor-base-url"),
    modelInput: document.getElementById("mentor-model"),
    apiKeyInput: document.getElementById("mentor-api-key"),
    manualConnectButton: document.getElementById("mentor-manual-connect"),
    connectionTestButton: document.getElementById("mentor-test-connection"),
    unlockPasswordInput: document.getElementById("mentor-unlock-password"),
    unlockButton: document.getElementById("mentor-unlock-button"),
    connectionStatus: document.getElementById("mentor-connection-status"),
    generateQuizButton: document.getElementById("mentor-generate-quiz"),
    quizStatus: document.getElementById("mentor-quiz-status"),
    quizContainer: document.getElementById("mentor-quiz-container"),
    feedbackOverall: document.getElementById("mentor-feedback-overall"),
    feedbackItems: document.getElementById("mentor-feedback-items"),
    followUpContainer: document.getElementById("mentor-follow-up-container"),
    chatLog: document.getElementById("mentor-chat-log"),
    chatInput: document.getElementById("mentor-chat-input"),
    chatSendButton: document.getElementById("mentor-chat-send"),
  };

  initialize();

  function initialize() {
    renderCourseIntro();
    toggleCard(ui.manualCard, Boolean(runtimeOptions.allow_manual));
    toggleCard(ui.injectedCard, Boolean(runtimeOptions.allow_injected));
    closeSidebar();

    if (!runtimeOptions.allow_manual && !runtimeOptions.allow_injected) {
      setConnectionStatus("这份课件没有可用的连接方式。请重新打包课件。", "error");
    } else {
      setConnectionStatus("尚未连接模型接口。请先手动填写或解锁默认连接。", "info");
    }

    if (ui.manualConnectButton) {
      ui.manualConnectButton.addEventListener("click", handleManualConnect);
    }
    if (ui.connectionTestButton) {
      ui.connectionTestButton.addEventListener("click", handleTestConnection);
    }
    if (ui.sidebarToggle) {
      ui.sidebarToggle.addEventListener("click", toggleSidebar);
    }
    if (ui.sidebarClose) {
      ui.sidebarClose.addEventListener("click", closeSidebar);
    }
    if (ui.sidebarBackdrop) {
      ui.sidebarBackdrop.addEventListener("click", closeSidebar);
    }
    if (ui.unlockButton) {
      ui.unlockButton.addEventListener("click", handleUnlockDefaultProfile);
    }
    if (ui.generateQuizButton) {
      ui.generateQuizButton.addEventListener("click", handleGenerateQuiz);
    }
    if (ui.chatSendButton) {
      ui.chatSendButton.addEventListener("click", handleChatSend);
    }
    if (ui.chatInput) {
      ui.chatInput.addEventListener("keydown", (event) => {
        if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
          event.preventDefault();
          handleChatSend();
        }
      });
    }
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeSidebar();
      }
    });
    Array.from(document.querySelectorAll('[data-open-mentor="true"]')).forEach((element) => {
      element.addEventListener("click", (event) => {
        event.preventDefault();
        openSidebar();
      });
    });
  }

  function openSidebar() {
    document.body.classList.add("mentor-sidebar-open");
    if (ui.classroom) {
      ui.classroom.setAttribute("aria-hidden", "false");
    }
    if (ui.sidebarToggle) {
      ui.sidebarToggle.setAttribute("aria-expanded", "true");
    }
    if (ui.sidebarBackdrop) {
      ui.sidebarBackdrop.classList.remove("mentor-hidden");
    }
  }

  function closeSidebar() {
    document.body.classList.remove("mentor-sidebar-open");
    if (ui.classroom) {
      ui.classroom.setAttribute("aria-hidden", "true");
    }
    if (ui.sidebarToggle) {
      ui.sidebarToggle.setAttribute("aria-expanded", "false");
    }
    if (ui.sidebarBackdrop) {
      ui.sidebarBackdrop.classList.add("mentor-hidden");
    }
  }

  function toggleSidebar() {
    if (document.body.classList.contains("mentor-sidebar-open")) {
      closeSidebar();
      return;
    }
    openSidebar();
  }

  function readJsonScript(id) {
    const node = document.getElementById(id);
    if (!node || !node.textContent) {
      return null;
    }
    try {
      return JSON.parse(node.textContent);
    } catch (_error) {
      return null;
    }
  }

  function toggleCard(element, visible) {
    if (!element) {
      return;
    }
    element.classList.toggle("mentor-hidden", !visible);
  }

  function renderCourseIntro() {
    if (!ui.intro) {
      return;
    }
    const sectionCount = Array.isArray(course.section_titles) ? course.section_titles.length : 0;
    const snippetCount = Array.isArray(course.source_snippets) ? course.source_snippets.length : 0;
    ui.intro.textContent = `这份课件《${course.title}》已经准备好导师模式。先完整阅读正文，再开始 6 题诊断。当前课件包含 ${sectionCount} 个章节锚点与 ${snippetCount} 条原文摘录。`;
  }

  function setConnectionStatus(message, tone) {
    if (!ui.connectionStatus) {
      return;
    }
    ui.connectionStatus.textContent = message;
    ui.connectionStatus.className = "mentor-status";
    if (tone) {
      ui.connectionStatus.classList.add(`mentor-status-${tone}`);
    }
  }

  function setQuizStatus(message, tone) {
    if (!ui.quizStatus) {
      return;
    }
    ui.quizStatus.textContent = message;
    ui.quizStatus.className = "mentor-status mentor-status-inline";
    if (tone) {
      ui.quizStatus.classList.add(`mentor-status-${tone}`);
    }
  }

  function setButtonBusy(button, busy, idleText, busyText) {
    if (!button) {
      return;
    }
    button.disabled = busy;
    button.textContent = busy ? busyText : idleText;
  }

  function enableInteractiveActions() {
    if (ui.generateQuizButton) {
      ui.generateQuizButton.disabled = false;
    }
    if (ui.chatSendButton) {
      ui.chatSendButton.disabled = false;
    }
  }

  function getManualConfig() {
    return normalizeConnectionShape({
      baseUrl: (ui.baseUrlInput?.value || "").trim(),
      model: (ui.modelInput?.value || "").trim(),
      apiKey: (ui.apiKeyInput?.value || "").trim(),
    });
  }

  function normalizeConnectionShape(connection) {
    return {
      baseUrl: String(connection?.baseUrl || connection?.base_url || "").trim(),
      model: String(connection?.model || "").trim(),
      apiKey: String(connection?.apiKey || connection?.api_key || "").trim(),
    };
  }

  function hasAnyManualInput() {
    return Boolean(
      (ui.baseUrlInput?.value || "").trim() ||
      (ui.modelInput?.value || "").trim() ||
      (ui.apiKeyInput?.value || "").trim()
    );
  }

  function resolveConnectionForTest() {
    if (hasAnyManualInput()) {
      const manualConnection = getManualConfig();
      validateConnection(manualConnection);
      return { connection: manualConnection, mode: "manual" };
    }
    if (state.connection) {
      validateConnection(state.connection);
      return { connection: state.connection, mode: state.connectionMode || "manual" };
    }
    throw new Error("请先填写连接信息，或先解锁默认连接。")
  }

  function validateConnection(connection) {
    if (!connection || !connection.baseUrl) {
      throw new Error("请填写 Base URL。");
    }
    if (!connection.model) {
      throw new Error("请填写模型名称。");
    }
    if (!connection.apiKey) {
      throw new Error("请填写 API Key。");
    }
  }

  function normalizeBaseUrl(baseUrl) {
    return baseUrl.replace(/\/+$/, "");
  }

  function formatConnectionSummary(connection) {
    if (!connection) {
      return "模型接口";
    }
    return `${connection.model} @ ${normalizeBaseUrl(connection.baseUrl)}`;
  }

  async function relayPost(path, payload) {
    let response;
    try {
      response = await fetch(`${relayUrl}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
    } catch (_error) {
      throw new Error(`本地连接服务不可用。请先运行 mentor_relay.py，默认地址是 ${relayUrl}。`);
    }

    let data;
    try {
      data = await response.json();
    } catch (_error) {
      throw new Error(`本地连接服务返回了非 JSON 响应（HTTP ${response.status}）。`);
    }

    if (!response.ok || data?.ok === false) {
      throw new Error(data?.message || `本地连接服务请求失败（HTTP ${response.status}）。`);
    }
    return data;
  }

  async function handleManualConnect() {
    try {
      const connection = getManualConfig();
      validateConnection(connection);
      state.connection = connection;
      state.connectionMode = "manual";
      enableInteractiveActions();
      openSidebar();
      setConnectionStatus(`已连接手动配置：${connection.model} @ ${normalizeBaseUrl(connection.baseUrl)}`, "success");
    } catch (error) {
      openSidebar();
      setConnectionStatus(error.message || "手动连接失败。", "error");
    }
  }

  async function handleTestConnection() {
    openSidebar();
    setButtonBusy(ui.connectionTestButton, true, "测试连接", "测试中...");
    try {
      const resolved = resolveConnectionForTest();
      const result = await relayPost("/v1/test-connection", { connection: resolved.connection });
      state.connection = resolved.connection;
      state.connectionMode = resolved.mode;
      enableInteractiveActions();
      const successMessage = result?.empty_content
        ? `连接测试成功：${resolved.connection.model} @ ${normalizeBaseUrl(resolved.connection.baseUrl)}（接口返回空内容，但连接本身可用）`
        : `连接测试成功：${resolved.connection.model} @ ${normalizeBaseUrl(resolved.connection.baseUrl)}（经由本地连接服务）`;
      setConnectionStatus(successMessage, "success");
    } catch (error) {
      setConnectionStatus(error.message || "连接测试失败。", "error");
    } finally {
      setButtonBusy(ui.connectionTestButton, false, "测试连接", "测试中...");
    }
  }

  async function handleUnlockDefaultProfile() {
    setButtonBusy(ui.unlockButton, true, "解锁默认连接", "正在解锁...");
    try {
      if (!runtimeOptions.allow_injected || !encryptedProfile) {
        throw new Error("这份课件没有嵌入默认配置。");
      }
      if (!window.crypto?.subtle) {
        throw new Error("当前浏览器不支持 Web Crypto，无法解锁默认配置。");
      }
      const password = (ui.unlockPasswordInput?.value || "").trim();
      if (!password) {
        throw new Error("请输入解锁口令。");
      }
      const connection = normalizeConnectionShape(await decryptProfile(password));
      validateConnection(connection);
      state.connection = connection;
      state.connectionMode = "injected";
      enableInteractiveActions();
      openSidebar();
      setConnectionStatus(`已解锁默认连接：${connection.model} @ ${normalizeBaseUrl(connection.baseUrl)}`, "success");
      if (ui.unlockPasswordInput) {
        ui.unlockPasswordInput.value = "";
      }
    } catch (error) {
      openSidebar();
      setConnectionStatus(error.message || "解锁失败。", "error");
    } finally {
      setButtonBusy(ui.unlockButton, false, "解锁默认连接", "正在解锁...");
    }
  }

  async function decryptProfile(password) {
    const encoder = new TextEncoder();
    const passwordKey = await window.crypto.subtle.importKey(
      "raw",
      encoder.encode(password),
      "PBKDF2",
      false,
      ["deriveKey"]
    );
    const key = await window.crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: base64ToBytes(encryptedProfile.salt_b64),
        iterations: encryptedProfile.iterations,
        hash: "SHA-256",
      },
      passwordKey,
      { name: "AES-GCM", length: 256 },
      false,
      ["decrypt"]
    );
    try {
      const decrypted = await window.crypto.subtle.decrypt(
        { name: "AES-GCM", iv: base64ToBytes(encryptedProfile.iv_b64) },
        key,
        base64ToBytes(encryptedProfile.ciphertext_b64)
      );
      const decoder = new TextDecoder();
      return JSON.parse(decoder.decode(decrypted));
    } catch (_error) {
      throw new Error("解锁失败，口令错误或默认配置已损坏。");
    }
  }

  function base64ToBytes(value) {
    const binary = atob(value);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return bytes;
  }

  function buildLessonContext(includeAssessment) {
    const lesson = {
      title: course.title,
      summary_text: course.summary_text,
      section_titles: course.section_titles,
      source_snippets: course.source_snippets,
      self_test_seed: course.self_test_seed,
      meta: course.meta,
    };
    if (includeAssessment && state.assessment) {
      lesson.latest_assessment = state.assessment;
    }
    return lesson;
  }

  function truncateText(value, limit) {
    const text = String(value || "").trim();
    if (!text) {
      return "";
    }
    if (!Number.isFinite(limit) || limit < 1 || text.length <= limit) {
      return text;
    }
    return `${text.slice(0, Math.max(limit - 1, 1)).trimEnd()}…`;
  }

  function buildAssessmentSnapshot(level) {
    const feedback = state.assessment?.feedback;
    if (!feedback) {
      return null;
    }
    const compactMode = level === "tight";
    const weakConcepts = Array.isArray(feedback.weak_concepts)
      ? feedback.weak_concepts.slice(0, compactMode ? 2 : 3).map((concept) => ({
          concept: truncateText(concept?.concept, 36),
          reason: truncateText(concept?.reason, compactMode ? 72 : 120),
          remedy: truncateText(concept?.remedy, compactMode ? 72 : 120),
        }))
      : [];
    const items = Array.isArray(feedback.items)
      ? feedback.items.slice(0, compactMode ? 2 : 3).map((item, index) => ({
          question_id: item?.question_id || `q${index + 1}`,
          diagnosis: truncateText(item?.diagnosis, compactMode ? 72 : 120),
          correction: truncateText(item?.correction, compactMode ? 72 : 120),
          follow_up_question: truncateText(item?.follow_up_question, compactMode ? 72 : 100),
        }))
      : [];
    return {
      overall: {
        score: feedback.overall?.score ?? null,
        mastery_level: String(feedback.overall?.mastery_level || "").trim(),
        summary: truncateText(feedback.overall?.summary, compactMode ? 120 : 180),
      },
      weak_concepts: weakConcepts,
      items,
    };
  }

  function buildChatLessonContext(level) {
    const compactMode = level === "tight";
    const sourceSnippets = Array.isArray(course.source_snippets)
      ? course.source_snippets.slice(0, compactMode ? 2 : 4).map((snippet, index) => ({
          id: String(snippet?.id || `src${index + 1}`),
          text: truncateText(snippet?.text, compactMode ? 140 : 240),
        }))
      : [];
    const lesson = {
      title: String(course.title || "").trim(),
      summary_text: truncateText(course.summary_text, compactMode ? 2800 : 6000),
      section_titles: Array.isArray(course.section_titles)
        ? course.section_titles.slice(0, compactMode ? 8 : 10).map((title) => truncateText(title, 60))
        : [],
      source_snippets: sourceSnippets,
      self_test_seed: Array.isArray(course.self_test_seed)
        ? course.self_test_seed.slice(0, compactMode ? 4 : 6).map((seed) => truncateText(seed, 60))
        : [],
      meta: course.meta,
    };
    const assessmentSnapshot = buildAssessmentSnapshot(level);
    if (assessmentSnapshot) {
      lesson.latest_assessment = assessmentSnapshot;
    }
    return lesson;
  }

  function buildConversationSnapshot(limit) {
    return state.chatHistory
      .filter((message) => {
        if (message?.role !== "user" && message?.role !== "assistant") {
          return false;
        }
        const text = String(message?.text || "");
        return !(message.role === "assistant" && text.startsWith("这次回答失败了："));
      })
      .slice(-limit)
      .map((message) => ({
        role: message.role,
        text: truncateText(message.text, 280),
      }));
  }

  function shouldRetryChat(error) {
    const message = String(error?.message || "").toLowerCase();
    return message.includes("timeout") || message.includes("timed out") || message.includes("超时") || message.includes("504");
  }

  async function requestMentorReply(question) {
    const attempts = [
      {
        level: "standard",
        conversationLimit: 4,
        options: { temperature: 0.45, maxTokens: 900, timeoutSeconds: 75 },
      },
      {
        level: "tight",
        conversationLimit: 2,
        options: { temperature: 0.35, maxTokens: 600, timeoutSeconds: 60 },
      },
    ];

    let lastError = null;
    for (let index = 0; index < attempts.length; index += 1) {
      const attempt = attempts[index];
      const payload = {
        lesson: buildChatLessonContext(attempt.level),
        conversation: buildConversationSnapshot(attempt.conversationLimit),
        user_question: question,
      };
      try {
        if (index > 0) {
          setConnectionStatus("检测到模型响应较慢，已自动缩短上下文后重试。", "info");
        }
        const reply = await callChatCompletion(
          [
            { role: "system", content: prompts.chat_system },
            { role: "user", content: JSON.stringify(payload, null, 2) },
          ],
          attempt.options,
        );
        setConnectionStatus(`已连接：${formatConnectionSummary(state.connection)}`, "success");
        return reply;
      } catch (error) {
        lastError = error;
        if (index >= attempts.length - 1 || !shouldRetryChat(error)) {
          throw error;
        }
      }
    }

    throw lastError || new Error("导师回答失败，请稍后再试。");
  }

  async function handleGenerateQuiz() {
    if (!state.connection) {
      openSidebar();
      setQuizStatus("请先连接模型接口。", "error");
      return;
    }
    openSidebar();
    setButtonBusy(ui.generateQuizButton, true, "开始 6 题诊断", "正在生成题目...");
    setQuizStatus("正在基于当前课件生成 6 题诊断式测验...", "info");
    try {
      const payload = {
        lesson: buildLessonContext(false),
        requirements: {
          question_count: 6,
          structure: [
            "2 concept understanding",
            "2 mechanism explanation",
            "1 scenario application",
            "1 teach-back question"
          ]
        },
        output_contract: prompts.quiz_output_contract,
      };
      const result = await callForJson(
        "quiz_generation",
        [
          { role: "system", content: prompts.quiz_system },
          { role: "user", content: JSON.stringify(payload, null, 2) },
        ],
        prompts.quiz_output_contract,
        { temperature: 0.35, maxTokens: 1400, timeoutSeconds: 90 }
      );
      if (!Array.isArray(result.questions) || result.questions.length !== 6) {
        throw new Error("题目返回不完整，请重试一次。");
      }
      state.questions = result.questions;
      renderQuiz(result.questions);
      openSidebar();
      setQuizStatus("题目已生成。请先逐题作答，再提交诊断答案。", "success");
    } catch (error) {
      openSidebar();
      setQuizStatus(error.message || "生成题目失败。", "error");
      ui.quizContainer.innerHTML = '<div class="mentor-empty">生成题目失败，请检查接口配置后重试。</div>';
    } finally {
      setButtonBusy(ui.generateQuizButton, false, "开始 6 题诊断", "正在生成题目...");
    }
  }

  function renderQuiz(questions) {
    const cards = questions.map((question, index) => {
      return `
        <div class="mentor-question-card">
          <div class="mentor-question-meta">
            <span class="mentor-badge">Q${index + 1}</span>
            <span class="mentor-badge">${escapeHtml(question.type || "short_answer")}</span>
            <span class="mentor-badge">${escapeHtml(question.concept || "概念点")}</span>
          </div>
          <div class="mentor-feedback-copy">${escapeHtml(question.question || "")}</div>
          <label class="mentor-label" for="mentor-answer-${index}">你的回答</label>
          <textarea id="mentor-answer-${index}" class="mentor-textarea" rows="5" data-question-id="${escapeAttribute(question.id || `q${index + 1}`)}"></textarea>
        </div>
      `;
    }).join("");

    ui.quizContainer.innerHTML = `
      <div class="mentor-quiz-list">${cards}</div>
      <div class="mentor-action-row">
        <button id="mentor-submit-quiz" class="mentor-button mentor-button-primary" type="button">提交诊断答案</button>
      </div>
    `;
    const submitButton = document.getElementById("mentor-submit-quiz");
    if (submitButton) {
      submitButton.addEventListener("click", handleSubmitQuiz);
    }
  }

  function collectAnswers() {
    return state.questions.map((question, index) => {
      const textarea = document.getElementById(`mentor-answer-${index}`);
      return {
        question_id: question.id || `q${index + 1}`,
        answer: (textarea?.value || "").trim(),
      };
    });
  }

  async function handleSubmitQuiz() {
    if (!state.connection || !state.questions.length) {
      openSidebar();
      return;
    }
    const answers = collectAnswers();
    if (answers.some((item) => !item.answer)) {
      setQuizStatus("还有空白答案。请至少为每一题写一点你的理解。", "error");
      return;
    }
    const submitButton = document.getElementById("mentor-submit-quiz");
    setButtonBusy(submitButton, true, "提交诊断答案", "正在讲评...");
    setQuizStatus("老师正在批改你的答案，并准备补讲与追问...", "info");
    try {
      const payload = {
        lesson: buildLessonContext(false),
        questions: state.questions,
        answers,
        output_contract: prompts.assessment_output_contract,
      };
      const result = await callForJson(
        "quiz_assessment",
        [
          { role: "system", content: prompts.assessment_system },
          { role: "user", content: JSON.stringify(payload, null, 2) },
        ],
        prompts.assessment_output_contract,
        { temperature: 0.2, maxTokens: 2200, timeoutSeconds: 120 }
      );
      state.assessment = {
        answers,
        feedback: result,
      };
      renderAssessment(result);
      openSidebar();
      setQuizStatus("讲评已生成。继续看补讲与追问题，或者直接去问老师。", "success");
    } catch (error) {
      openSidebar();
      setQuizStatus(error.message || "讲评失败，请重试。", "error");
    } finally {
      setButtonBusy(submitButton, false, "提交诊断答案", "正在讲评...");
    }
  }

  function renderAssessment(feedback) {
    const overall = feedback.overall || {};
    const mastery = overall.mastery_level || "developing";
    ui.feedbackOverall.innerHTML = `
      <div class="mentor-feedback-card">
        <div class="mentor-feedback-header">
          <div>
            <div class="mentor-kicker">Overall Review</div>
            <h4>总体掌握度：${escapeHtml(mastery)}</h4>
          </div>
          <div class="mentor-score">${escapeHtml(String(overall.score ?? "--"))}</div>
        </div>
        <div class="mentor-feedback-copy">${escapeHtml(overall.summary || "暂无总体讲评。")}</div>
      </div>
    `;

    const items = Array.isArray(feedback.items) ? feedback.items : [];
    ui.feedbackItems.innerHTML = items.map((item, index) => `
      <div class="mentor-feedback-card">
        <div class="mentor-feedback-header">
          <div>
            <div class="mentor-kicker">Question ${index + 1}</div>
            <h4>得分：${escapeHtml(String(item.score ?? "--"))}</h4>
          </div>
          <span class="mentor-badge">${escapeHtml(item.question_id || `q${index + 1}`)}</span>
        </div>
        <div class="mentor-stack">
          <div><strong>误区诊断</strong><div class="mentor-feedback-copy">${escapeHtml(item.diagnosis || "")}</div></div>
          <div><strong>正确理解</strong><div class="mentor-feedback-copy">${escapeHtml(item.correction || "")}</div></div>
          <div><strong>导师补讲</strong><div class="mentor-feedback-copy">${escapeHtml(item.mini_lesson || "")}</div></div>
          <div><strong>追问题</strong><div class="mentor-feedback-copy">${escapeHtml(item.follow_up_question || "")}</div></div>
        </div>
      </div>
    `).join("");

    const weakConcepts = Array.isArray(feedback.weak_concepts) ? feedback.weak_concepts : [];
    const followUpItems = items.filter((item) => item.follow_up_question);
    ui.followUpContainer.innerHTML = `
      ${weakConcepts.length ? `
      <div class="mentor-feedback-card">
        <div class="mentor-kicker">Weak Concepts</div>
        <div class="mentor-stack">
          ${weakConcepts.map((concept) => `
            <div>
              <strong>${escapeHtml(concept.concept || "薄弱概念")}</strong>
              <div class="mentor-feedback-copy">原因：${escapeHtml(concept.reason || "")}</div>
              <div class="mentor-feedback-copy">补强：${escapeHtml(concept.remedy || "")}</div>
            </div>
          `).join("")}
        </div>
      </div>
      ` : ""}
      ${followUpItems.length ? `
      <div class="mentor-feedback-card">
        <div class="mentor-kicker">Follow-up Practice</div>
        <div class="mentor-follow-up-grid">
          ${followUpItems.map((item, index) => `
            <div class="mentor-follow-up-card">
              <strong>${escapeHtml(item.question_id || `q${index + 1}`)}</strong>
              <div class="mentor-feedback-copy">${escapeHtml(item.follow_up_question || "")}</div>
              <label class="mentor-label" for="mentor-follow-up-answer-${index}">你的继续作答</label>
              <textarea id="mentor-follow-up-answer-${index}" class="mentor-textarea" rows="4"></textarea>
              <div class="mentor-action-row">
                <button class="mentor-button mentor-button-secondary mentor-follow-up-submit" type="button" data-follow-up-index="${index}">请求导师点评</button>
              </div>
              <div id="mentor-follow-up-result-${index}" class="mentor-status mentor-hidden"></div>
            </div>
          `).join("")}
        </div>
      </div>
      ` : ""}
    `;

    Array.from(document.querySelectorAll(".mentor-follow-up-submit")).forEach((button) => {
      button.addEventListener("click", handleFollowUpSubmit);
    });
  }

  async function handleFollowUpSubmit(event) {
    const button = event.currentTarget;
    const index = Number(button.getAttribute("data-follow-up-index"));
    const feedbackItems = Array.isArray(state.assessment?.feedback?.items) ? state.assessment.feedback.items : [];
    const targetItem = feedbackItems.filter((item) => item.follow_up_question)[index];
    const answerBox = document.getElementById(`mentor-follow-up-answer-${index}`);
    const resultBox = document.getElementById(`mentor-follow-up-result-${index}`);
    const answer = (answerBox?.value || "").trim();
    if (!targetItem || !resultBox) {
      return;
    }
    if (!answer) {
      resultBox.textContent = "请先写下你的继续作答。";
      resultBox.className = "mentor-status mentor-status-error";
      resultBox.classList.remove("mentor-hidden");
      return;
    }
    setButtonBusy(button, true, "请求导师点评", "点评中...");
    resultBox.className = "mentor-status mentor-status-info";
    resultBox.classList.remove("mentor-hidden");
    resultBox.textContent = "老师正在看你的追问答案...";
    try {
      const payload = {
        lesson: buildLessonContext(true),
        follow_up_question: targetItem.follow_up_question,
        learner_answer: answer,
        original_question_id: targetItem.question_id,
        output_contract: prompts.follow_up_output_contract,
      };
      const result = await callForJson(
        "follow_up_review",
        [
          { role: "system", content: prompts.follow_up_system },
          { role: "user", content: JSON.stringify(payload, null, 2) },
        ],
        prompts.follow_up_output_contract,
        { temperature: 0.2, maxTokens: 900, timeoutSeconds: 90 }
      );
      resultBox.className = "mentor-status mentor-status-success";
      resultBox.textContent = `${result.verdict || "improving"}\n${result.feedback || ""}\n下一步：${result.next_step || "继续用自己的话复述一遍。"}`;
    } catch (error) {
      resultBox.className = "mentor-status mentor-status-error";
      resultBox.textContent = error.message || "导师点评失败，请稍后再试。";
    } finally {
      setButtonBusy(button, false, "请求导师点评", "点评中...");
    }
  }

  async function handleChatSend() {
    if (!state.connection) {
      openSidebar();
      setConnectionStatus("请先连接模型接口。", "error");
      return;
    }
    const question = (ui.chatInput?.value || "").trim();
    if (!question) {
      return;
    }
    appendChatMessage("user", question);
    openSidebar();
    if (ui.chatInput) {
      ui.chatInput.value = "";
    }
    setButtonBusy(ui.chatSendButton, true, "问老师", "老师思考中...");
    try {
      const reply = await requestMentorReply(question);
      appendChatMessage("assistant", reply);
    } catch (error) {
      appendChatMessage("assistant", `这次回答失败了：${error.message || "未知错误"}`);
    } finally {
      setButtonBusy(ui.chatSendButton, false, "问老师", "老师思考中...");
    }
  }

  function appendChatMessage(role, text) {
    state.chatHistory.push({ role, text });
    if (state.chatHistory.length > 20) {
      state.chatHistory = state.chatHistory.slice(-20);
    }
    if (!ui.chatLog) {
      return;
    }
    ui.chatLog.innerHTML = state.chatHistory.map((message) => `
      <div class="mentor-chat-bubble mentor-chat-bubble-${message.role === "user" ? "user" : "assistant"}">
        <span class="mentor-chat-role">${message.role === "user" ? "你" : "老师"}</span>
        <div class="mentor-chat-message">${escapeHtml(message.text)}</div>
      </div>
    `).join("");
  }

  async function callForJson(taskName, messages, outputContract, options) {
    const rawText = await callChatCompletion(messages, options);
    const parsedDirect = tryParseJson(rawText);
    if (parsedDirect) {
      return parsedDirect;
    }
    const repairPayload = {
      task: taskName,
      output_contract: outputContract,
      original_output: rawText,
    };
    const repaired = await callChatCompletion(
      [
        { role: "system", content: prompts.json_repair_system },
        { role: "user", content: JSON.stringify(repairPayload, null, 2) },
      ],
      { temperature: 0, maxTokens: options?.maxTokens || 1200, timeoutSeconds: Math.min(options?.timeoutSeconds || 60, 90) }
    );
    const repairedParsed = tryParseJson(repaired);
    if (repairedParsed) {
      return repairedParsed;
    }
    throw new Error("模型返回了无法修复的非 JSON 内容，请重试一次。");
  }

  function tryParseJson(value) {
    if (!value || typeof value !== "string") {
      return null;
    }
    const direct = safeJsonParse(value);
    if (direct) {
      return direct;
    }
    const fenceMatch = value.match(/```(?:json)?\s*([\s\S]*?)```/i);
    if (fenceMatch?.[1]) {
      const fenced = safeJsonParse(fenceMatch[1]);
      if (fenced) {
        return fenced;
      }
    }
    const firstBrace = value.indexOf("{");
    const lastBrace = value.lastIndexOf("}");
    if (firstBrace >= 0 && lastBrace > firstBrace) {
      const objectSlice = safeJsonParse(value.slice(firstBrace, lastBrace + 1));
      if (objectSlice) {
        return objectSlice;
      }
    }
    const firstBracket = value.indexOf("[");
    const lastBracket = value.lastIndexOf("]");
    if (firstBracket >= 0 && lastBracket > firstBracket) {
      return safeJsonParse(value.slice(firstBracket, lastBracket + 1));
    }
    return null;
  }

  function safeJsonParse(value) {
    try {
      return JSON.parse(value);
    } catch (_error) {
      return null;
    }
  }

  async function callChatCompletionWithConnection(connection, messages, options) {
    validateConnection(connection);
    const result = await relayPost("/v1/chat", {
      connection,
      messages,
      options: options || {},
    });
    if (!result?.content) {
      throw new Error("本地连接服务已响应，但没有返回可读内容。");
    }
    return result.content;
  }

  async function callChatCompletion(messages, options) {
    return await callChatCompletionWithConnection(state.connection, messages, options);
  }

  function extractAssistantText(payload) {
    if (typeof payload?.output_text === "string" && payload.output_text.trim()) {
      return payload.output_text.trim();
    }
    if (Array.isArray(payload?.output)) {
      const collected = [];
      for (const item of payload.output) {
        const content = Array.isArray(item?.content) ? item.content : [];
        for (const segment of content) {
          if (typeof segment?.text === "string" && segment.text.trim()) {
            collected.push(segment.text.trim());
          }
        }
      }
      if (collected.length) {
        return collected.join("\n").trim();
      }
    }
    const messageContent = payload?.choices?.[0]?.message?.content;
    if (typeof messageContent === "string") {
      return messageContent.trim();
    }
    if (Array.isArray(messageContent)) {
      return messageContent.map((item) => item?.text || item?.content || "").join("\n").trim();
    }
    return "";
  }

  function escapeHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/\"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function escapeAttribute(value) {
    return escapeHtml(value).replace(/\s+/g, "-");
  }
})();
