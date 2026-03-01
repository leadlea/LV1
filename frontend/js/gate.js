/**
 * ゲーティングロジック - レベル合格状態の取得と表示制御
 * Lv1は常に表示。Lv2〜Lv4はバックエンドの合格状態に基づいて表示/非表示を切り替える。
 */
const Gate = (() => {
  /**
   * sessionStorageからセッションIDを取得する。
   * 存在しない場合はnullを返す。
   * @returns {string|null}
   */
  function getSessionId() {
    try {
      const raw = sessionStorage.getItem("ai_levels_session");
      if (!raw) return null;
      const data = JSON.parse(raw);
      return data.session_id || null;
    } catch {
      return null;
    }
  }

  /**
   * 全レベルクリア判定
   * @param {object} levels - { lv1: {unlocked, passed}, lv2: ..., lv3: ..., lv4: ... }
   * @returns {boolean}
   */
  function checkAllLevelsClear(levels) {
    return levels.lv1 && levels.lv1.passed &&
           levels.lv2 && levels.lv2.passed &&
           levels.lv3 && levels.lv3.passed &&
           levels.lv4 && levels.lv4.passed;
  }

  /**
   * レベルカードの表示状態を更新する
   * @param {object} levels - { lv1: {unlocked, passed}, lv2: ..., lv3: ..., lv4: ... }
   */
  function updateLevelCards(levels) {
    for (const [key, info] of Object.entries(levels)) {
      const card = document.getElementById(`level-${key}`);
      if (!card) continue;

      if (info.unlocked) {
        card.hidden = false;
        card.classList.remove("level-card--locked");
        card.classList.add("level-card--unlocked");
      } else {
        // ロック中のレベルは非表示のまま
        card.hidden = true;
      }

      // 合格済みステータス表示
      if (info.passed) {
        const statusEl = document.getElementById(`status-${key}`);
        if (statusEl) {
          statusEl.textContent = "✅ 合格済み";
          statusEl.classList.add("level-card__status--passed");
        }
      }
    }

    // 全レベルクリア時の祝福メッセージ
    if (checkAllLevelsClear(levels)) {
      const header = document.querySelector(".index-content__header");
      if (header && !document.getElementById("all-clear-banner")) {
        const banner = document.createElement("div");
        banner.id = "all-clear-banner";
        banner.style.cssText = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: #fff; padding: 1.5rem; border-radius: 10px; text-align: center; margin-bottom: 1.5rem;";
        banner.innerHTML = '<div style="font-size: 2rem; margin-bottom: 0.5rem;">🎉🏆🎉</div><h2 style="margin: 0 0 0.5rem; font-size: 1.3rem;">全レベルクリア！おめでとうございます！</h2><p style="margin: 0; opacity: 0.9;">AI Levelsカリキュラム全体を修了しました。</p>';
        header.after(banner);
      }
    }
  }

  /**
   * デフォルト状態を適用する（API呼び出し前、またはセッションIDがない場合）
   * Lv1のみ表示、Lv2〜Lv4は非表示
   */
  function applyDefaultState() {
    updateLevelCards({
      lv1: { unlocked: true, passed: false },
      lv2: { unlocked: false, passed: false },
      lv3: { unlocked: false, passed: false },
      lv4: { unlocked: false, passed: false },
    });
  }

  /**
   * バックエンドAPIからレベル状態を取得し、UIを更新する
   */
  async function loadLevelStatus() {
    const sessionId = getSessionId();

    if (!sessionId) {
      applyDefaultState();
      return;
    }

    try {
      ApiClient.hideError();
      const data = await ApiClient.getLevelsStatus(sessionId);
      updateLevelCards(data.levels);
    } catch (err) {
      // API失敗時はデフォルト状態（Lv1のみ表示）にフォールバック
      applyDefaultState();
      ApiClient.showError(
        "レベル状態の取得に失敗しました。",
        () => loadLevelStatus()
      );
    }
  }

  /**
   * 初期化 - ページ読み込み時に実行
   */
  function init() {
    applyDefaultState();
    loadLevelStatus();
  }

  // DOM読み込み完了後に初期化
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  return { loadLevelStatus, getSessionId };
})();
