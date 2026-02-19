/**
 * Lv1 カリキュラム実行 - メインアプリケーションロジック
 * セッション管理、出題→回答→採点→レビューのフロー制御
 * 全ステップ完了時のみ /lv1/complete を呼び出してDB保存
 */
const Lv1App = (() => {
  // --- セッション管理 ---

  const SESSION_KEY = "ai_levels_session";

  /** UUID v4 生成 */
  function generateUUID() {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
      const r = (Math.random() * 16) | 0;
      return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
    });
  }

  /** セッションデータを取得。なければ新規作成 */
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

  function saveSession(session) {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
  }

  // --- DOM参照 ---

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
    els.questionOptions = document.getElementById("question-options");
    els.textareaWrap = document.getElementById("textarea-wrap");
    els.answerText = document.getElementById("answer-text");
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
  }

  // --- セクション表示制御 ---

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

  // --- 設問タイプのラベル ---

  const TYPE_LABELS = {
    multiple_choice: "選択問題",
    free_text: "自由記述",
    scenario: "シナリオ",
  };

  // --- 設問表示 ---

  function renderQuestion(question, stepIndex, totalSteps) {
    updateProgress(stepIndex + 1, totalSteps);

    els.questionStep.textContent = `ステップ ${question.step}`;
    els.questionType.textContent = TYPE_LABELS[question.type] || question.type;
    els.questionPrompt.textContent = question.prompt;

    // コンテキスト
    if (question.context) {
      els.questionContext.textContent = question.context;
      els.questionContext.hidden = false;
    } else {
      els.questionContext.hidden = true;
    }

    // 選択肢 or テキストエリア
    if (question.type === "multiple_choice" && question.options) {
      els.questionOptions.innerHTML = "";
      question.options.forEach((opt, i) => {
        const label = document.createElement("label");
        label.className = "option-label";
        label.innerHTML =
          `<input type="radio" name="mc-answer" value="${i}">` +
          `<span class="option-text">${escapeHtml(opt)}</span>`;
        els.questionOptions.appendChild(label);
      });
      els.questionOptions.hidden = false;
      els.textareaWrap.hidden = true;
    } else {
      els.questionOptions.hidden = true;
      els.textareaWrap.hidden = false;
      els.answerText.value = "";
    }

    els.btnSubmit.disabled = true;
    showSection("question");
  }

  function escapeHtml(str) {
    const d = document.createElement("div");
    d.textContent = str;
    return d.innerHTML;
  }

  // --- 回答取得 ---

  function getAnswer(question) {
    if (question.type === "multiple_choice" && question.options) {
      const checked = document.querySelector('input[name="mc-answer"]:checked');
      return checked ? question.options[parseInt(checked.value, 10)] : null;
    }
    return els.answerText.value.trim() || null;
  }

  // --- 入力バリデーション ---

  function setupInputListeners() {
    // ラジオボタン変更
    els.questionOptions.addEventListener("change", () => {
      els.btnSubmit.disabled = false;
    });
    // テキストエリア入力
    els.answerText.addEventListener("input", () => {
      els.btnSubmit.disabled = els.answerText.value.trim().length === 0;
    });
  }

  // --- 採点結果表示 ---

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

  // --- 最終結果表示 ---

  function renderFinal(session) {
    const passedCount = session.grades.filter((g) => g.passed).length;
    const totalSteps = session.questions.length;
    const allPassed = passedCount === totalSteps;

    els.finalIcon.textContent = allPassed ? "🎉" : "📝";
    els.finalTitle.textContent = allPassed ? "Lv1 合格！" : "Lv1 結果";
    els.finalMessage.textContent = allPassed
      ? "おめでとうございます！全ステップに合格しました。"
      : `${passedCount} / ${totalSteps} ステップに合格しました。`;

    // サマリー
    let summaryHtml = "";
    session.questions.forEach((q, i) => {
      const g = session.grades[i];
      const icon = g && g.passed ? "✅" : "❌";
      const score = g ? g.score : "-";
      summaryHtml +=
        `<div class="summary-row">` +
        `<span>ステップ ${q.step}</span>` +
        `<span>${icon} ${score}点</span>` +
        `</div>`;
    });
    els.finalSummary.innerHTML = summaryHtml;

    updateProgress(totalSteps, totalSteps);
    showSection("final");
  }

  // --- メインフロー ---

  let session = null;

  async function start() {
    cacheDom();
    setupInputListeners();
    session = getSession();

    // 既に設問がある場合は途中から再開
    if (session.questions.length > 0 && session.current_step < session.questions.length) {
      renderQuestion(session.questions[session.current_step], session.current_step, session.questions.length);
      return;
    }

    // 既に全ステップ完了済みの場合
    if (session.questions.length > 0 && session.current_step >= session.questions.length) {
      renderFinal(session);
      return;
    }

    // 新規: テスト・ドリル生成
    showSection("loading");
    try {
      ApiClient.hideError();
      const data = await ApiClient.generate(session.session_id);
      session.questions = data.questions || [];
      session.current_step = 0;
      saveSession(session);

      if (session.questions.length === 0) {
        ApiClient.showError("設問の生成に失敗しました。", () => start());
        return;
      }

      renderQuestion(session.questions[0], 0, session.questions.length);
    } catch (err) {
      showSection("loading");
      ApiClient.showError(
        "テスト・ドリルの生成に失敗しました。ネットワーク接続を確認してください。",
        () => start()
      );
    }
  }

  /** 回答送信 → 採点 */
  async function submitAnswer() {
    const question = session.questions[session.current_step];
    const answer = getAnswer(question);
    if (!answer) return;

    els.btnSubmit.disabled = true;
    els.btnSubmit.textContent = "採点中...";

    try {
      ApiClient.hideError();
      const result = await ApiClient.grade(
        session.session_id,
        question.step,
        question,
        answer
      );

      session.answers.push(answer);
      session.grades.push(result);
      saveSession(session);

      renderResult(result);
    } catch (err) {
      els.btnSubmit.disabled = false;
      els.btnSubmit.textContent = "回答を送信";
      ApiClient.showError(
        "採点に失敗しました。もう一度お試しください。",
        () => submitAnswer()
      );
    }
  }

  /** 次のステップへ進む or 完了処理 */
  async function nextStep() {
    session.current_step += 1;
    saveSession(session);

    if (session.current_step >= session.questions.length) {
      // 全ステップ完了 → DB保存
      await completeSession();
    } else {
      els.btnSubmit.textContent = "回答を送信";
      renderQuestion(
        session.questions[session.current_step],
        session.current_step,
        session.questions.length
      );
    }
  }

  /** 全ステップ完了時のみDB保存 */
  async function completeSession() {
    showSection("loading");
    document.querySelector(".lv1-loading-text").textContent = "結果を保存しています...";

    const allPassed = session.grades.every((g) => g.passed);

    try {
      ApiClient.hideError();
      await ApiClient.complete({
        session_id: session.session_id,
        questions: session.questions,
        answers: session.answers,
        grades: session.grades,
        final_passed: allPassed,
      });
    } catch (err) {
      // 保存失敗してもフロントでは結果を表示する（要件5.4: リトライ可能な旨を通知）
      ApiClient.showError(
        "結果の保存に失敗しました。リトライボタンで再試行できます。",
        () => completeSession()
      );
    }

    renderFinal(session);
  }

  // --- イベントバインド ---

  function bindEvents() {
    document.getElementById("btn-submit").addEventListener("click", submitAnswer);
    document.getElementById("btn-next").addEventListener("click", nextStep);
  }

  // --- 初期化 ---

  function init() {
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
