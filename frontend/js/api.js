/**
 * API通信層 - セルフチェックシステム
 */

function showError(msg) {
  const banner = document.getElementById("error-banner");
  if (banner) {
    banner.textContent = msg;
    banner.classList.add("show");
  }
}

function hideError() {
  const banner = document.getElementById("error-banner");
  if (banner) banner.classList.remove("show");
}

async function apiFetch(path, options = {}) {
  hideError();
  const url = window.API_BASE_URL + path;
  try {
    const resp = await fetch(url, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.error || `HTTP ${resp.status}`);
    }
    return data;
  } catch (err) {
    showError(err.message || "通信エラーが発生しました。接続を確認してください。");
    throw err;
  }
}

async function submitSelfcheck(sessionId, track, answers) {
  return apiFetch("/selfcheck/submit", {
    method: "POST",
    body: JSON.stringify({
      session_id: sessionId,
      track: track,
      answers: answers,
    }),
  });
}

async function getDefinitions() {
  return apiFetch("/selfcheck/definitions");
}
