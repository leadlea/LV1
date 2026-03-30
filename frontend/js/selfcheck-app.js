/**
 * セルフチェックアプリロジック
 * Session管理、トラック選択、回答収集、API送信
 */

const SESSION_KEY = "selfcheck_session";

const SessionManager = {
  init() {
    let session = this.get();
    if (!session || !session.session_id) {
      session = {
        session_id: crypto.randomUUID(),
        started_at: new Date().toISOString(),
      };
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    }
    // URLクエリからuser_id取得
    const params = new URLSearchParams(window.location.search);
    const userId = params.get("user_id");
    if (userId) {
      session.user_id = userId;
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    }
    return session;
  },
  get() {
    try {
      return JSON.parse(sessionStorage.getItem(SESSION_KEY));
    } catch { return null; }
  },
  setTrack(track) {
    const session = this.get();
    if (session) {
      session.track = track;
      sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
    }
  },
  getTrack() {
    const s = this.get();
    return s ? s.track : null;
  },
  getSessionId() {
    const s = this.get();
    return s ? s.session_id : null;
  },
};

/* チェック項目定義（フロントエンド用） */
const COMMON_ITEMS = [
  { id: "common_1", text: "生成AIの基本的な仕組みと限界を理解している" },
  { id: "common_2", text: "生成AIを業務で安全に利用するためのルールを理解している" },
  { id: "common_3", text: "プロンプトを工夫して目的に合った出力を得られる" },
  { id: "common_4", text: "生成AIの出力を批判的に評価し、正確性を検証できる" },
  { id: "common_5", text: "生成AIを使って業務の効率化を実践している" },
  { id: "common_6", text: "生成AIの活用事例を他者に説明・共有できる" },
];

const BUSINESS_ITEMS = [
  { id: "biz_1", text: "AIを活用した情報収集・要約で業務判断を効率化している" },
  { id: "biz_2", text: "AIを活用して提案資料・報告書の品質を向上させている" },
  { id: "biz_3", text: "AIを活用してプロジェクト計画・タスク分解を行っている" },
  { id: "biz_4", text: "AIを活用した業務改善の提案・実行ができる" },
  { id: "biz_5", text: "AIを活用してコミュニケーション品質を向上させている" },
  { id: "biz_6", text: "AI活用のベストプラクティスをチームに展開している" },
];

const ENGINEER_ITEMS = [
  { id: "eng_1", text: "AIによる開発・運用支援ツールを日常的に活用している" },
  { id: "eng_2", text: "AIを活用したレビュー・テスト・品質管理を実践している" },
  { id: "eng_3", text: "AIを活用したアーキテクチャ設計・技術選定を行っている" },
  { id: "eng_4", text: "AI/MLモデルの評価・選定・統合ができる" },
  { id: "eng_5", text: "AIを活用した開発・運用プロセスの標準化・自動化を推進している" },
  { id: "eng_6", text: "AI技術の社内導入・技術支援をリードしている" },
];

const RATING_LABELS = [
  { value: 0, label: "未経験" },
  { value: 1, label: "知っている" },
  { value: 2, label: "使っている" },
  { value: 3, label: "成果を出している" },
  { value: 4, label: "周囲に展開できる" },
];

function getItemsForTrack(track) {
  const trackItems = track === "business" ? BUSINESS_ITEMS : ENGINEER_ITEMS;
  return [...COMMON_ITEMS, ...trackItems];
}

function renderCheckItems(containerId, track) {
  const container = document.getElementById(containerId);
  if (!container) return;
  const items = getItemsForTrack(track);
  container.innerHTML = "";

  items.forEach((item, idx) => {
    const section = idx < 6 ? "共通" : (track === "business" ? "ビジネス" : "エンジニア");
    const div = document.createElement("div");
    div.className = "check-item";
    div.dataset.itemId = item.id;

    let ratingHtml = RATING_LABELS.map(r =>
      `<label class="rating-label" data-value="${r.value}">
        <span class="score">${r.value}</span>
        <span class="label">${r.label}</span>
      </label>`
    ).join("");

    div.innerHTML = `
      <div class="check-item-text">${idx < 6 ? "【共通】" : `【${section}】`} ${item.text}</div>
      <div class="rating-group">${ratingHtml}</div>
    `;
    container.appendChild(div);
  });

  // Rating click handlers
  container.querySelectorAll(".rating-label").forEach(label => {
    label.addEventListener("click", () => {
      const group = label.closest(".rating-group");
      group.querySelectorAll(".rating-label").forEach(l => l.classList.remove("selected"));
      label.classList.add("selected");
      label.closest(".check-item").classList.remove("error");
    });
  });
}

function collectAnswers() {
  const answers = {};
  let hasError = false;
  document.querySelectorAll(".check-item").forEach(item => {
    const id = item.dataset.itemId;
    const selected = item.querySelector(".rating-label.selected");
    if (!selected) {
      item.classList.add("error");
      hasError = true;
    } else {
      answers[id] = parseInt(selected.dataset.value);
    }
  });
  return hasError ? null : answers;
}

function showLoading(show) {
  const el = document.getElementById("loading");
  if (el) el.style.display = show ? "block" : "none";
  const btn = document.getElementById("submit-btn");
  if (btn) btn.disabled = show;
}

/**
 * 共通項目とトラック別項目を別コンテナに分割レンダリング
 */
function renderCheckItemsSplit(commonContainerId, trackContainerId, track) {
  const commonContainer = document.getElementById(commonContainerId);
  const trackContainer = document.getElementById(trackContainerId);
  if (!commonContainer || !trackContainer) return;

  const trackItems = track === "business" ? BUSINESS_ITEMS : ENGINEER_ITEMS;

  function renderItems(container, items, startIdx) {
    container.innerHTML = "";
    items.forEach((item, i) => {
      const num = startIdx + i + 1;
      const div = document.createElement("div");
      div.className = "check-item";
      div.dataset.itemId = item.id;

      const ratingHtml = RATING_LABELS.map(r =>
        `<label class="rating-label" data-value="${r.value}">
          <span class="score">${r.value}</span>
          <span class="label">${r.label}</span>
        </label>`
      ).join("");

      div.innerHTML = `
        <div class="check-item-text"><span class="check-item-num">${num}</span>${item.text}</div>
        <div class="rating-group">${ratingHtml}</div>
      `;
      container.appendChild(div);
    });

    container.querySelectorAll(".rating-label").forEach(label => {
      label.addEventListener("click", () => {
        const group = label.closest(".rating-group");
        group.querySelectorAll(".rating-label").forEach(l => l.classList.remove("selected"));
        label.classList.add("selected");
        label.closest(".check-item").classList.remove("error");
      });
    });
  }

  renderItems(commonContainer, COMMON_ITEMS, 0);
  renderItems(trackContainer, trackItems, 6);
}
