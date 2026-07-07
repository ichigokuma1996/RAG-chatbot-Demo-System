import { useEffect, useMemo, useRef, useState } from "react";
import { endSession, fetchInsights, sendChatMessage } from "./api";
import { getOrCreateSessionId, resetSessionId } from "./session";

const initialBotMessage = {
  id: 1,
  role: "bot",
  content:
    "こんにちは。DataPro Solutions サポートAIです。ログイン、請求、機能要望、バグ、契約についてお気軽にご相談ください。",
};

function App() {
  const [activePage, setActivePage] = useState("chat");
  const [sessionId, setSessionId] = useState(getOrCreateSessionId);
  const [messages, setMessages] = useState([initialBotMessage]);
  const [inputText, setInputText] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [showRatingModal, setShowRatingModal] = useState(false);
  const [rating, setRating] = useState(0);
  const [isEnded, setIsEnded] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [latestAnalysis, setLatestAnalysis] = useState(null);
  const [insights, setInsights] = useState([]);
  const [insightsLoading, setInsightsLoading] = useState(false);

  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (activePage === "insights") {
      loadInsights();
    }
  }, [activePage]);

  const insightSummary = useMemo(() => {
    const total = insights.length;
    const negative = insights.filter((item) => item.sentiment === "negative").length;
    const high = insights.filter((item) => item.urgency === "high").length;
    const categoryCount = {};

    insights.forEach((item) => {
      categoryCount[item.category] = (categoryCount[item.category] || 0) + 1;
    });

    const topCategory =
      Object.entries(categoryCount).sort((a, b) => b[1] - a[1])[0]?.[0] || "-";

    return { total, negative, high, topCategory };
  }, [insights]);

  async function handleSend() {
    const text = inputText.trim();

    if (!text || isSending || isEnded) {
      return;
    }

    const userMessage = {
      id: Date.now(),
      role: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setIsSending(true);
    setErrorMessage("");

    try {
      const data = await sendChatMessage({
        sessionId,
        message: text,
      });

      const sourceText =
        data.sources && data.sources.length > 0
          ? `\n\n参照FAQ: ${data.sources.join(" / ")}`
          : "";

      const botMessage = {
        id: Date.now() + 1,
        role: "bot",
        content: `${data.reply}${sourceText}`,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (error) {
      setErrorMessage(
        "バックエンドに接続できません。FastAPI が http://localhost:8000 で起動しているか確認してください。"
      );
    } finally {
      setIsSending(false);
    }
  }

  function handleKeyDown(event) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  function handleEndConversation() {
    if (!isEnded) {
      setShowRatingModal(true);
    }
  }

  async function handleSubmitRating() {
    if (rating < 1 || rating > 5) {
      return;
    }

    setIsSending(true);
    setErrorMessage("");

    try {
      const data = await endSession({
        sessionId,
        rating,
      });

      setLatestAnalysis(data.analysis);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now(),
          role: "bot",
          content:
            "ご利用ありがとうございました。会話内容を分析し、カスタマーサクセスチーム向けのインサイトとして保存しました。",
        },
      ]);
      setIsEnded(true);
      setShowRatingModal(false);
    } catch (error) {
      setErrorMessage("会話終了処理に失敗しました。バックエンドの状態を確認してください。");
    } finally {
      setIsSending(false);
    }
  }

  function handleStartNewConversation() {
    const nextSessionId = resetSessionId();

    setSessionId(nextSessionId);
    setMessages([{ ...initialBotMessage, id: Date.now() }]);
    setInputText("");
    setRating(0);
    setIsEnded(false);
    setErrorMessage("");
    setShowRatingModal(false);
    setLatestAnalysis(null);
  }

  async function loadInsights() {
    setInsightsLoading(true);
    setErrorMessage("");

    try {
      const data = await fetchInsights();
      setInsights(data);
    } catch (error) {
      setErrorMessage("分析データを取得できません。バックエンドを起動してください。");
    } finally {
      setInsightsLoading(false);
    }
  }

  return (
    <div className="app">
      <aside className="sidebar">
        <div>
          <div className="brand">DataPro Solutions</div>
          <h1>Intelligent Chatbot</h1>
          <p>Customer Success Support</p>

          <nav className="nav-buttons">
            <button
              className={activePage === "chat" ? "active" : ""}
              onClick={() => setActivePage("chat")}
            >
              チャット
            </button>
            <button
              className={activePage === "insights" ? "active" : ""}
              onClick={() => setActivePage("insights")}
            >
              分析
            </button>
          </nav>

          <div className="session-box">
            <span>Session ID</span>
            <strong>{sessionId}</strong>
          </div>
        </div>

        <div className="sidebar-actions">
          {activePage === "chat" && (
            <>
              <button
                className="end-button"
                onClick={handleEndConversation}
                disabled={isEnded}
              >
                会話を終了
              </button>

              {isEnded && (
                <button className="new-button" onClick={handleStartNewConversation}>
                  新しい会話
                </button>
              )}
            </>
          )}
        </div>
      </aside>

      {activePage === "chat" ? (
        <main className="chat-area">
          <header className="chat-header">
            <div>
              <h2>お問い合わせチャット</h2>
              <p>AI が FAQ を参照しながら一次回答します。</p>
            </div>
            <span className={isEnded ? "status-ended" : "status-active"}>
              {isEnded ? "終了済み" : "対応中"}
            </span>
          </header>

          <section className="messages">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`message-row ${
                  message.role === "user" ? "user-row" : "bot-row"
                }`}
              >
                <div className={`message-bubble ${message.role}`}>
                  {message.content}
                </div>
              </div>
            ))}

            {isSending && (
              <div className="message-row bot-row">
                <div className="message-bubble bot">回答を生成しています...</div>
              </div>
            )}

            {latestAnalysis && <AnalysisCard analysis={latestAnalysis} />}

            <div ref={chatEndRef} />
          </section>

          {errorMessage && <div className="error-message">{errorMessage}</div>}

          <footer className="chat-input-area">
            <textarea
              value={inputText}
              onChange={(event) => setInputText(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                isEnded
                  ? "この会話は終了しました。"
                  : "メッセージを入力してください。例: ログインできません"
              }
              disabled={isSending || isEnded}
            />

            <button onClick={handleSend} disabled={isSending || isEnded}>
              送信
            </button>
          </footer>
        </main>
      ) : (
        <main className="insights-area">
          <header className="chat-header">
            <div>
              <h2>顧客インサイト分析</h2>
              <p>終了した会話から課題、感情、緊急度を確認します。</p>
            </div>
            <button className="refresh-button" onClick={loadInsights}>
              更新
            </button>
          </header>

          {errorMessage && <div className="error-message">{errorMessage}</div>}

          <section className="summary-grid">
            <SummaryCard label="総会話数" value={insightSummary.total} />
            <SummaryCard label="Negative" value={insightSummary.negative} />
            <SummaryCard label="High 緊急度" value={insightSummary.high} />
            <SummaryCard label="最多カテゴリ" value={insightSummary.topCategory} />
          </section>

          <section className="insight-list">
            {insightsLoading && <div className="empty-state">読み込み中...</div>}
            {!insightsLoading && insights.length === 0 && (
              <div className="empty-state">
                まだ分析データがありません。チャットを終了するとここに表示されます。
              </div>
            )}
            {!insightsLoading &&
              insights.map((item) => (
                <article className="insight-item" key={item.session_id}>
                  <div className="insight-head">
                    <strong>{item.category}</strong>
                    <span>{item.urgency}</span>
                  </div>
                  <p>{item.summary}</p>
                  <dl>
                    <dt>ユーザー課題</dt>
                    <dd>{item.user_need}</dd>
                    <dt>感情</dt>
                    <dd>{item.sentiment}</dd>
                    <dt>満足度</dt>
                    <dd>{item.satisfaction}</dd>
                    <dt>隠れた課題</dt>
                    <dd>{item.hidden_topic}</dd>
                    <dt>推奨アクション</dt>
                    <dd>{item.recommended_action}</dd>
                  </dl>
                </article>
              ))}
          </section>
        </main>
      )}

      {showRatingModal && (
        <div className="modal-overlay">
          <div className="rating-modal">
            <h3>満足度を評価してください</h3>
            <p>今回のサポートはいかがでしたか？</p>

            <div className="stars">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  className={star <= rating ? "active" : ""}
                  onClick={() => setRating(star)}
                  aria-label={`${star} star`}
                >
                  ★
                </button>
              ))}
            </div>

            <div className="modal-actions">
              <button
                type="button"
                className="cancel-button"
                onClick={() => setShowRatingModal(false)}
              >
                キャンセル
              </button>

              <button
                type="button"
                className="submit-button"
                onClick={handleSubmitRating}
                disabled={rating === 0 || isSending}
              >
                送信
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function SummaryCard({ label, value }) {
  return (
    <div className="summary-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function AnalysisCard({ analysis }) {
  return (
    <div className="analysis-card">
      <h3>会話分析結果</h3>
      <div className="analysis-grid">
        <span>カテゴリ</span>
        <strong>{analysis.category}</strong>
        <span>感情</span>
        <strong>{analysis.sentiment}</strong>
        <span>満足度</span>
        <strong>{analysis.satisfaction}</strong>
        <span>緊急度</span>
        <strong>{analysis.urgency}</strong>
      </div>
      <p>{analysis.hidden_topic}</p>
    </div>
  );
}

export default App;
