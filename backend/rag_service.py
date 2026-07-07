import json
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

FAQ_PATH = Path(__file__).resolve().parent / "data" / "faqs.json"


def load_faqs() -> list[dict]:
    with FAQ_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


class RagChatService:
    def __init__(self) -> None:
        self.faqs = load_faqs()
        self.chain = self._build_langchain_chain()

    def _build_langchain_chain(self):
        api_key = os.getenv("OPENAI_API_KEY")

        if not api_key:
            print("[AI] OPENAI_API_KEY is not set. fallback mode.", flush=True)
            return None

        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_openai import ChatOpenAI
        except Exception as error:
            print(f"[AI] LangChain import error: {error}", flush=True)
            return None

        model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        print(f"[AI] LangChain mode enabled. model={model_name}", flush=True)

        llm = ChatOpenAI(model=model_name, temperature=0.3)

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """
あなたはBtoB SaaS企業 DataPro Solutions のカスタマーサポートAIです。

役割:
- ユーザーの問い合わせに自然な日本語で回答する
- FAQ情報がある場合は、それを優先して回答する
- FAQ情報がない場合でも、一般的なカスタマーサポートAIとして自然に回答する
- 不明点がある場合は、必要な情報をユーザーに質問する
- 緊急、契約、重大なバグ、請求トラブルの場合は、担当者に引き継ぐ可能性を伝える

禁止:
- FAQに完全一致しないという理由だけで回答を拒否しない
- 同じ定型文だけを繰り返さない
- 根拠がない企業固有情報を断定しない
""",
                ),
                (
                    "human",
                    """
会話履歴:
{history}

企業FAQ / RAG参考情報:
{context}

ユーザーの最新メッセージ:
{question}

上記を踏まえて、自然なカスタマーサポート回答をしてください。
""",
                ),
            ]
        )

        return prompt | llm

    def answer(self, message: str, history: list[dict]) -> dict:
        docs = self.retrieve(message)
        need_human = self.should_escalate(message, docs)

        print(
            f"[RAG] message={message} docs={len(docs)} need_human={need_human}",
            flush=True,
        )

        if self.chain:
            try:
                response = self.chain.invoke(
                    {
                        "history": self.format_history(history),
                        "context": self.format_docs(docs),
                        "question": message,
                    }
                )

                return {
                    "reply": response.content,
                    "need_human": need_human,
                    "sources": [doc["title"] for doc in docs],
                }

            except Exception as error:
                print(f"[AI ERROR] {error}", flush=True)
                return {
                    "reply": (
                        "大模型の呼び出し中にエラーが発生しました。"
                        "API key、モデル名、またはネットワーク設定を確認してください。"
                    ),
                    "need_human": True,
                    "sources": [doc["title"] for doc in docs],
                }

        return {
            "reply": self.fallback_reply(docs, need_human),
            "need_human": need_human,
            "sources": [doc["title"] for doc in docs],
        }

    def retrieve(self, message: str, top_k: int = 3) -> list[dict]:
        text = message.lower()
        scored_docs = []

        for faq in self.faqs:
            score = 0

            for keyword in faq["keywords"]:
                if keyword.lower() in text:
                    score += 3

            if faq["category"].lower() in text:
                score += 2

            if score > 0:
                scored_docs.append((score, faq))

        scored_docs.sort(key=lambda item: item[0], reverse=True)
        return [faq for _, faq in scored_docs[:top_k]]

    def should_escalate(self, message: str, docs: list[dict]) -> bool:
        text = message.lower()

        escalation_words = [
            "緊急",
            "至急",
            "急ぎ",
            "障害",
            "本番",
            "止まる",
            "使えない",
            "解約",
            "返金",
            "契約変更",
            "担当者",
            "人間",
            "クレーム",
            "重大",
        ]

        if any(word.lower() in text for word in escalation_words):
            return True

        if docs and docs[0]["category"] in ["契約", "バグ"]:
            return True

        return False

    def fallback_reply(self, docs: list[dict], need_human: bool) -> str:
        if docs:
            best = docs[0]
            reply = (
                f"{best['category']}に関するお問い合わせですね。\n\n"
                f"{best['answer']}\n\n"
                "追加で状況を教えていただければ、もう少し具体的に案内できます。"
            )
        else:
            reply = (
                "現在は大模型APIが未設定のため、簡易モードで応答しています。\n\n"
                "ログイン、請求、機能要望、バグ、契約に関する内容であれば、"
                "FAQをもとに回答できます。"
            )

        if need_human:
            reply += "\n\nこの内容は担当者への引き継ぎ対象になる可能性があります。"

        return reply

    def format_docs(self, docs: list[dict]) -> str:
        if not docs:
            return "関連するFAQは見つかりませんでした。ただし、FAQがなくても通常のサポートAIとして回答してください。"

        lines = []
        for doc in docs:
            lines.append(
                f"- カテゴリ: {doc['category']}\n"
                f"  タイトル: {doc['title']}\n"
                f"  回答: {doc['answer']}"
            )

        return "\n".join(lines)

    def format_history(self, history: list[dict], max_messages: int = 8) -> str:
        if not history:
            return "まだ会話履歴はありません。"

        recent = history[-max_messages:]
        lines = []

        for item in recent:
            role = "ユーザー" if item["role"] == "user" else "AI"
            lines.append(f"{role}: {item['content']}")

        return "\n".join(lines)
