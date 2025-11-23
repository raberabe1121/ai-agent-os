# AI Agent OS (MTA-based Message Operating System)

**AI Agent OS** は、Postfix + LMTP を中心とした  
「メッセージ駆動型の AI オペレーティングシステム」です。

従来の HTTP API ベースではなく、  
**メール配送 (MTA) を IPC（プロセス間通信）として再利用し、  
AI の行動ログ・イベント・状態変化を “メッセージとして配送” する**  
まったく新しいアーキテクチャを提供します。

---

## 🚀 Overview

AI Agent OS は次の思想で設計されています：

### ⭐ 1. **Everything is a Message**
AI の行動、Webhook、ActivityPub、cron、外部API結果など  
全てのイベントは「メッセージ（Envelope）」として MTA に投入されます。

Postfix → LMTP → Worker → Storage → Web UI  
という流れで全てが動作します。

### ⭐ 2. **Email-grade Reliability for AI**
HTTP より堅牢な MTA の特性（再送・キュー・遅延耐性）を  
AI システム全体のメッセージ基盤として活用。

### ⭐ 3. **AI エージェントを OS の “プロセス” として扱う**
- ひとつひとつの AI は “Inbox” を持ち、
- メッセージを受信して “行動” を決め、
- 結果をまたメッセージとして発信する。

UNIX のプロセス間通信のように AI を連携可能。

### ⭐ 4. **ActivityPub / Email / AI の統合**
SNS 投稿・通知・AI 自動返信・Notion 連携が  
全て同じメッセージ基盤で動作します。

---

## 🏗️ System Architecture
┌────────┐ ┌───────────────┐
│ Postfix │──→ │ LMTP Handler │──→ Worker (Python)
└────────┘ └───────────────┘
│
▼
AI Message Envelope
│
▼
Storage (S3 / RDS)
│
▼
Web Dashboard


---

## 📦 Main Components

### 1. **LMTP Handler**
`/script/ai_message_envelope.py`  
Postfix から受け取ったメールを構造化メッセージ（Envelope）へ変換。

- JSON 形式
- AI エージェント間通信に特化
- デバッグしやすく軽量

### 2. **AI Message Envelope v0.1**
```json
{
  "id": "uuid",
  "from": "agent://inbox/xxx",
  "to": "agent://inbox/yyy",
  "type": "follow | post | command | event",
  "payload": { ... },
  "time": "ISO8601"
}
```
### 3. Workers
- メッセージルーティング
- ActivityPub 変換
- AI 自動応答
- Notion 等の SaaS 更新

### 4. Web UI
- 受信メッセージ閲覧
- AI エージェントの状態可視化
- ActivityPub / メール的フロント

