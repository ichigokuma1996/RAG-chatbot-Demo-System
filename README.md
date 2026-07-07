# DataPro Intelligent Chatbot System

## できること

- React のチャット画面から問い合わせを送信
- FastAPI 後端で会話を SQLite に保存
- FAQ データを検索して RAG 形式で回答
- LangChain + OpenAI API が設定されていれば大模型で回答
- 会話終了時に満足度を受け取り、カテゴリ・感情・緊急度・隠れた課題を分析
- 管理者画面で分析結果を一覧表示

## フォルダ構成

```text
datapro-chatbot-system/
  backend/
    app.py
    database.py
    rag_service.py
    analysis_service.py
    schemas.py
    data/faqs.json
    requirements.txt
    .env.example
  frontend/
    index.html
    package.json
    vite.config.js
    src/
      App.jsx
      App.css
      api.js
      session.js
      main.jsx
```

## 起動方法

### 1. バックエンド

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```

OpenAI API key を使う場合は `backend/.env` に入れます。

```text
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
```

API key を入れなくても、簡易ルール版でチャットと分析は動きます。

### 2. フロントエンド

```bash
cd frontend
npm install
npm run dev
```

ブラウザで表示される Vite の URL を開きます。通常は以下です。

```text
http://localhost:5173
```

## API

### POST `/api/chat`

```json
{
  "session_id": "session-xxx",
  "message": "ログインできません"
}
```

### POST `/api/end_session`

```json
{
  "session_id": "session-xxx",
  "rating": 4
}
```
