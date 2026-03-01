/**
 * Lv2 カリキュラム実行 - ケーススタディ形式
 * セッション管理、出題→回答→採点→レビューの4ステップフロー制御
 * 全ステップ完了時のみ /lv2/complete を呼び出してDB保存
 */
const Lv2App = (() => {
  const SESSION_KEY = "ai_levels_lv2_session";
  const LV1_SESSION_KEY = "ai_levels_session";

  const STEP_LABELS = {
    1: "業務プロセス設計",
    2: "AI実行指示",
    3: "成果物検証",
    4: "改善サイクル",
  };

  const TYPE_LABELS = { scenario: "シナリオ", free_text: "自由記述" };

  function generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  function getSession() {
    try {
      const raw = sessionStorage.getItem(SESSION_KEY);
      if (raw) return JSON.parse(raw);
    } catch { /* ignore */ }
    const session = {
      session_id: generateUUID(),
      current_step: 0,
      questions: [],
      answers: [],
      grades: [],
      started_at: new Date().toISOString(),
    };
    saveSession(session);
    return session;
  }

  function saveSession(s) {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
  }

  /** Check Lv1 pass status; redirect if not passed */
  async function checkLv1Gate() {
    let sessionId = null;
    try {
      const raw = sessionStorage.getItem(LV1_SESSION_KEY);
      if (raw) sessionId = JSON.parse(raw).session_id;
    } catch { /* ignore */ }
    if (!sessionId) { window.location.href = "index.html"; return false; }
    try {
      const data = await ApiClient.getLevelsStatus(sessionId);
      if (!data.levels || !data.levels.lv2 || !data.levels.lv2.unlocked) {
        window.location.href = "index.html"; return false;
      }
      return true;
    } catch {
      window.location.href = "index.html"; return false;
    }
  }

  const els = {};

  function cacheDom() {
    els.loading = document.getElementById("section-loading");
    els.questionSection = document.getElementById("section-question");
    els.resultSection = document.getElementById("section-result");
    els.finalSection = document.getElementById("section-final");
    els.progressFill = document.getElementById("progress-fill");
    els.progressLabel = document.getElementById("progress-label");
    els.progressBar = document.getElementById("progress-bar");
    els.questionStep = document.getElementById("question-step");
    els.questionType = document.getElementById("question-type");
    els.questionContext = document.getElementById("question-context");
    els.questionPrompt = document.getElementById("question-prompt");
    els.textareaWrap = document.getElementById("textarea-wrap");
    els.answerText = document.getElementById("answer-text");
    els.charCount = document.getElementById("char-count");
    els.btnSubmit = document.getElementById("btn-submit");
    els.resultVerdict = document.getElementById("result-verdict");
    els.resultScore = document.getElementById("result-score");
    els.resultFeedback = document.getElementById("result-feedback");
    els.resultExplanation = document.getElementById("result-explanation");
    els.btnNext = document.getElementById("btn-next");
    els.finalIcon = document.getElementById("final-icon");
    els.finalTitle = document.getElementById("final-title");
    els.finalMessage = document.getElementById("final-message");
    els.finalSummary = document.getElementById("final-summary");
    els.stepsContainer = document.getElementById("lv2-steps");
  }

  function showSection(name) {
    els.loading.hidden = name !== "loading";
    els.questionSection.hidden = name !== "question";
    els.resultSection.hidden = name !== "result";
    els.finalSection.hidden = name !== "final";
  }

  function updateProgress(current, total) {
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    els.progressFill.style.width = pct + "%";
    els.progressLabel.textContent = `ステップ ${current} / ${total}`;
    els.progressBar.setAttribute("aria-valuenow", pct);
  }

  function updateStepIndicators(currentIdx) {
    const items = els.stepsContainer.querySelectorAll(".lv2-steps__item");
    items.forEach((item, i) => {
      item.classList.remove("lv2-steps__item--active", "lv2-steps__item--done");
      if (i < currentIdx) item.classList.add("lv2-steps__item--done");
      else if (i === currentIdx) item.classList.add("lv2-steps__item--active");
    });
  }

  function renderQuestion(question, stepIndex, totalSteps) {
    updateProgress(stepIndex + 1, totalSteps);
    updateStepIndicators(stepIndex);

    els.questionStep.textContent = `ステップ ${question.step} — ${STEP_LABELS[question.step] || ""}`;
    els.questionType.textContent = TYPE_LABELS[question.type] || question.type;
    els.questionPrompt.textContent = question.prompt;

    if (question.context) {
      els.questionContext.textContent = question.context;
      els.questionContext.hidden = false;
    } else {
      els.questionContext.hidden = true;
    }

    els.textareaWrap.hidden = false;
    els.answerText.value = "";
    els.charCount.textContent = "0 文字";
    els.btnSubmit.disabled = true;
    showSection("question");
  }

  function renderResult(gradeResult) {
    if (gradeResult.passed) {
      els.resultVerdict.textContent = "✅ 合格";
      els.resultVerdict.className = "result-card__verdict result-card__verdict--passed";
    } else {
      els.resultVerdict.textContent = "❌ 不合格";
      els.resultVerdict.className = "result-card__verdict result-card__verdict--failed";
    }
    els.resultScore.textContent = `スコア: ${gradeResult.score} / 100`;
    els.resultFeedback.textContent = gradeResult.feedback || "";
    els.resultExplanation.textContent = gradeResult.explanation || "";
    showSection("result");
  }

  function renderFinal(session) {
    const passedCount = session.grades.filter((g) => g.passed).length;
    const totalSteps = session.questions.length;
    const allPassed = passedCount === totalSteps;

    updateStepIndicators(totalSteps);

    els.finalIcon.textContent = allPassed ? "🎉" : "📝";
    els.finalTitle.textContent = allPassed ? "Lv2 合格！" : "Lv2 結果";
    els.finalMessage.textContent = allPassed
      ? "おめでとうございます！全基準に合格しました。"
      : `${passedCount} / ${totalSteps} 基準に合格しました。`;

    let summaryHtml = "";
    session.questions.forEach((q, i) => {
      const g = session.grades[i];
      const icon = g && g.passed ? "✅" : "❌";
      const score = g ? g.score : "-";
      const label = STEP_LABELS[q.step] || `ステップ ${q.step}`;
      summaryHtml +=
        `<div class="summary-row">` +
        `<span>${label}</span>` +
        `<span>${icon} ${score}点</span>` +
        `</div>`;
    });
    els.finalSummary.innerHTML = summaryHtml;

    updateProgress(totalSteps, totalSteps);
    showSection("final");
  }

  let session = null;

  async function start() {
    cacheDom();
    setupInputListeners();
    session = getSession();

    if (session.questions.length > 0 && session.current_step < session.questions.length) {
      renderQuestion(session.questions[session.current_step], session.current_step, session.questions.length);
      return;
    }
    if (session.questions.length > 0 && session.current_step >= session.questions.length) {
      renderFinal(session);
      return;
    }

    showSection("loading");
    try {
      ApiClient.hideError();
      const data = await ApiClient.lv2Generate(session.session_id);
      session.questions = data.questions || [];
      session.current_step = 0;
      saveSession(session);

      if (session.questions.length === 0) {
        ApiClient.showError("設問の生成に失敗しました。", () => start());
        return;
      }
      renderQuestion(session.questions[0], 0, session.questions.length);
    } catch (err) {
      showSection("question");
      if (err.status && err.status >= 500) {
        ApiClient.showError("サーバーエラーが発生しました。しばらく待ってからリトライしてください。", () => start());
      } else if (err.status) {
        ApiClient.showError("ケーススタディの生成に失敗しました。(" + err.status + ")", () => start());
      } else {
        ApiClient.showError("ネットワーク接続を確認してください。", () => start());
      }
    }
  }

  async function submitAnswer() {
    const question = session.questions[session.current_step];
    const answer = els.answerText.value.trim();
    if (!answer) return;

    els.btnSubmit.disabled = true;
    els.btnSubmit.textContent = "採点中...";

    try {
      ApiClient.hideError();
      const result = await ApiClient.lv2Grade(session.session_id, question.step, question, answer);
      session.answers.push(answer);
      session.grades.push(result);
      saveSession(session);
      renderResult(result);
    } catch (err) {
      els.btnSubmit.disabled = false;
      els.btnSubmit.textContent = "回答を送信";
      ApiClient.showError("採点に失敗しました。もう一度お試しください。", () => submitAnswer());
    }
  }

  async function nextStep() {
    session.current_step += 1;
    saveSession(session);

    if (session.current_step >= session.questions.length) {
      await completeSession();
    } else {
      els.btnSubmit.textContent = "回答を送信";
      renderQuestion(session.questions[session.current_step], session.current_step, session.questions.length);
    }
  }

  async function completeSession() {
    showSection("loading");
    document.querySelector(".lv2-loading-text").textContent = "結果を保存しています...";

    const allPassed = session.grades.every((g) => g.passed);

    try {
      ApiClient.hideError();
      await ApiClient.lv2Complete({
        session_id: session.session_id,
        questions: session.questions,
        answers: session.answers,
        grades: session.grades,
        final_passed: allPassed,
      });
    } catch (err) {
      ApiClient.showError("結果の保存に失敗しました。リトライボタンで再試行できます。", () => completeSession());
    }

    renderFinal(session);
  }

  function setupInputListeners() {
    // Textarea input + char count
    document.getElementById("answer-text").addEventListener("input", function () {
      const len = this.value.trim().length;
      document.getElementById("char-count").textContent = `${this.value.length} 文字`;
      document.getElementById("btn-submit").disabled = len === 0;
    });
  }

  function bindEvents() {
    document.getElementById("btn-submit").addEventListener("click", submitAnswer);
    document.getElementById("btn-next").addEventListener("click", nextStep);
  }

  async function init() {
    const passed = await checkLv1Gate();
    if (!passed) return;
    bindEvents();
    start();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return { getSession, start };
})();
