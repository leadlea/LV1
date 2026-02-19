/**
 * API クライアント - バックエンドAPIとの通信を担当
 * 認証なし（Lv1はログイン不要）
 */
const ApiClient = (() => {
  // API Gateway のベースURL（デプロイ後に設定）
  const BASE_URL = window.API_BASE_URL || "";

  /**
   * 共通 fetch ラッパー
   * @param {string} path - エンドポイントパス
   * @param {object} options - fetch オプション
   * @returns {Promise<object>} レスポンスJSON
   */
  async function request(path, options = {}) {
    const url = `${BASE_URL}${path}`;
    const defaultHeaders = { "Content-Type": "application/json" };

    const res = await fetch(url, {
      ...options,
      headers: { ...defaultHeaders, ...options.headers },
    });

    const data = await res.json();

    if (!res.ok) {
      const err = new Error(data.error || `HTTP ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }

    return data;
  }

  /**
   * POST /lv1/generate - テスト・ドリル生成
   * @param {string} sessionId
   * @returns {Promise<{session_id: string, questions: Array}>}
   */
  function generate(sessionId) {
    return request("/lv1/generate", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId }),
    });
  }

  /**
   * POST /lv1/grade - 回答採点+レビュー
   * @param {string} sessionId
   * @param {number} step
   * @param {object} question
   * @param {string} answer
   * @returns {Promise<{session_id: string, step: number, passed: boolean, score: number, feedback: string, explanation: string}>}
   */
  function grade(sessionId, step, question, answer) {
    return request("/lv1/grade", {
      method: "POST",
      body: JSON.stringify({ session_id: sessionId, step, question, answer }),
    });
  }

  /**
   * POST /lv1/complete - 完了レコード保存
   * @param {object} payload - { session_id, questions, answers, grades, final_passed }
   * @returns {Promise<{saved: boolean, record_id: string}>}
   */
  function complete(payload) {
    return request("/lv1/complete", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }

  /**
   * GET /levels/status - レベル合格状態取得
   * @param {string} sessionId
   * @returns {Promise<{levels: object}>}
   */
  function getLevelsStatus(sessionId) {
    return request(`/levels/status?session_id=${encodeURIComponent(sessionId)}`);
  }

  /**
   * エラーバナーを表示する
   * @param {string} message - エラーメッセージ
   * @param {Function} onRetry - リトライ時のコールバック
   */
  function showError(message, onRetry) {
    const banner = document.getElementById("error-banner");
    const msgEl = document.getElementById("error-message");
    const retryBtn = document.getElementById("error-retry-btn");

    if (!banner || !msgEl) return;

    msgEl.textContent = message;
    banner.hidden = false;

    if (retryBtn && onRetry) {
      const newBtn = retryBtn.cloneNode(true);
      retryBtn.parentNode.replaceChild(newBtn, retryBtn);
      newBtn.addEventListener("click", () => {
        banner.hidden = true;
        onRetry();
      });
    }
  }

  /**
   * エラーバナーを非表示にする
   */
  function hideError() {
    const banner = document.getElementById("error-banner");
    if (banner) banner.hidden = true;
  }

  return { generate, grade, complete, getLevelsStatus, showError, hideError };
})();
