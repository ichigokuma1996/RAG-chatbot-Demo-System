import json
import os
import re

from dotenv import load_dotenv


load_dotenv()

CATEGORIES = ["ログイン", "請求", "機能要望", "バグ", "契約", "その他"]
SENTIMENTS = ["positive", "neutral", "negative"]
URGENCIES = ["low", "medium", "high"]


class ConversationAnalyzer:
    def __init__(self) -> None:
        self.chain = self._build_langchain_chain()

    def _build_langchain_chain(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return None

        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_openai import ChatOpenAI
        except Exception:
            return None

        llm = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "あなたはBtoB SaaSのカスタマーサクセス分析担当です。"
                    "会話を分析して、必ずJSONだけを返してください。",
                ),
                (
                    "human",
                    """
会話:
{conversation}

ユーザー満足度 rating: {rating} / 5

次のJSON形式で返してください。
category は ログイン / 請求 / 機能要望 / バグ / 契約 / その他 のどれか。
sentiment は positive / neutral / negative のどれか。
urgency は low / medium / high のどれか。

{{
  "category": "...",
  "user_need": "...",
  "sentiment": "...",
  "satisfaction": 0,
  "urgency": "...",
  "summary": "...",
  "hidden_topic": "...",
  "recommended_action": "..."
}}
""",
                ),
            ]
        )
        return prompt | llm

    def analyze(self, session_id: str, messages: list[dict], rating: int) -> dict:
        conversation = self.format_conversation(messages)

        if self.chain:
            try:
                response = self.chain.invoke({"conversation": conversation, "rating": rating})
                data = self.parse_json(response.content)
                if data:
                    return self.normalize_result(session_id, data, rating)
            except Exception:
                pass

        return self.rule_based_analysis(session_id, messages, rating)

    def format_conversation(self, messages: list[dict]) -> str:
        lines = []
        for item in messages:
            role = "ユーザー" if item["role"] == "user" else "AI"
            lines.append(f"{role}: {item['content']}")
        return "\n".join(lines)

    def parse_json(self, text: str) -> dict | None:
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if not match:
                return None
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None

    def normalize_result(self, session_id: str, data: dict, rating: int) -> dict:
        category = data.get("category", "その他")
        sentiment = data.get("sentiment", "neutral")
        urgency = data.get("urgency", "medium")

        if category not in CATEGORIES:
            category = "その他"
        if sentiment not in SENTIMENTS:
            sentiment = "neutral"
        if urgency not in URGENCIES:
            urgency = "medium"

        satisfaction = data.get("satisfaction", rating * 20)
        try:
            satisfaction = int(satisfaction)
        except (TypeError, ValueError):
            satisfaction = rating * 20

        return {
            "session_id": session_id,
            "category": category,
            "user_need": data.get("user_need") or "ユーザーの課題を確認する必要があります。",
            "sentiment": sentiment,
            "satisfaction": max(0, min(100, satisfaction)),
            "urgency": urgency,
            "summary": data.get("summary") or "会話内容の要約はありません。",
            "hidden_topic": data.get("hidden_topic") or "追加確認が必要です。",
            "recommended_action": data.get("recommended_action") or "担当者が会話内容を確認してください。",
        }

    def rule_based_analysis(self, session_id: str, messages: list[dict], rating: int) -> dict:
        user_texts = [item["content"] for item in messages if item["role"] == "user"]
        text = "\n".join(user_texts)
        lower_text = text.lower()

        category = self.detect_category(lower_text)
        sentiment = self.detect_sentiment(lower_text, rating)
        urgency = self.detect_urgency(lower_text, category, sentiment)
        satisfaction = rating * 20
        user_need = self.extract_user_need(user_texts)

        hidden_topics = {
            "ログイン": "認証手順やパスワード再設定導線が分かりにくい可能性があります。",
            "請求": "請求情報の表示や支払い状況の説明が不足している可能性があります。",
            "機能要望": "既存機能だけでは業務フローを十分に支援できていない可能性があります。",
            "バグ": "特定画面や操作で品質問題が発生している可能性があります。",
            "契約": "契約変更やプラン内容の説明が分かりにくい可能性があります。",
            "その他": "FAQにない問い合わせテーマが発生している可能性があります。",
        }

        actions = {
            "ログイン": "ログイン画面とFAQにパスワード再設定の案内を追加する。",
            "請求": "請求書確認方法と支払い反映タイミングをFAQに明記する。",
            "機能要望": "要望内容をプロダクトチームに共有し、類似要望の件数を追跡する。",
            "バグ": "発生画面、操作手順、時刻を確認し、担当者へ優先的に連携する。",
            "契約": "契約担当者へ引き継ぎ、希望変更内容と時期を確認する。",
            "その他": "会話内容を確認し、新しいFAQ候補として登録する。",
        }

        return {
            "session_id": session_id,
            "category": category,
            "user_need": user_need,
            "sentiment": sentiment,
            "satisfaction": satisfaction,
            "urgency": urgency,
            "summary": f"ユーザーは「{user_need}」について問い合わせています。",
            "hidden_topic": hidden_topics[category],
            "recommended_action": actions[category],
        }

    def detect_category(self, text: str) -> str:
        rules = [
            ("ログイン", ["ログイン", "login", "パスワード", "認証", "サインイン", "入れない"]),
            ("請求", ["請求", "invoice", "支払い", "料金", "決済", "billing"]),
            ("機能要望", ["機能", "要望", "追加", "改善", "feature", "欲しい"]),
            ("バグ", ["バグ", "bug", "エラー", "動かない", "不具合", "障害"]),
            ("契約", ["契約", "プラン", "解約", "更新", "見積", "contract"]),
        ]
        for category, keywords in rules:
            if any(keyword.lower() in text for keyword in keywords):
                return category
        return "その他"

    def detect_sentiment(self, text: str, rating: int) -> str:
        negative_words = ["困", "できない", "動かない", "遅い", "エラー", "不満", "怒", "最悪"]
        positive_words = ["ありがとう", "助か", "便利", "良い", "解決", "満足"]

        if rating <= 2 or any(word in text for word in negative_words):
            return "negative"
        if rating >= 4 or any(word in text for word in positive_words):
            return "positive"
        return "neutral"

    def detect_urgency(self, text: str, category: str, sentiment: str) -> str:
        high_words = ["緊急", "至急", "急ぎ", "本番", "障害", "止まる", "使えない"]
        if any(word in text for word in high_words):
            return "high"
        if category in ["バグ", "契約"] and sentiment == "negative":
            return "high"
        if category in ["請求", "契約", "バグ"]:
            return "medium"
        return "low"

    def extract_user_need(self, user_texts: list[str]) -> str:
        if not user_texts:
            return "問い合わせ内容が不足しています。"

        latest = user_texts[-1].strip()
        if len(latest) <= 80:
            return latest
        return latest[:80] + "..."
