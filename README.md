# AI Agent Hub - MTA-based Message Hub

## 概要
**AI Agent Hub** は、メール（SMTP/LMTP）を高速・信頼性の高いメッセージバスとして利用し、AIエージェントの行動・タスク・イベントを **メッセージ指向で処理するための OS レイヤー** です。

従来の Webhook / REST ではなく、**Postfix + LMTP + Queue + Worker** という MTA アーキテクチャを基盤にすることで、以下を実現します：

- 100% メッセージ駆動の AI アクションルーティング
- メール＝AI間通信の標準フォーマット（Envelope）
- 完全非同期・高耐久（MTA の再送・キュー管理）
- エージェント同士の連携と状態管理
- ローカル/クラウドどちらでも動作する分散OSとしての性質

本プロジェクトの目的は **“AIの行動をつなぐミドルウェア層”** を構築すること。
AIエージェントが分散して存在する時代の基盤となる、新しい OS の形を目指します。

---

## アーキテクチャ概要
```
┌──────────┐     SMTP       ┌─────────────┐
│  Agent Sender │ ───────────▶ │   Postfix MTA │
└──────────┘                 └──────┬────────┘
                                      │ LMTP
                                      ▼
                            ┌──────────────────┐
                            │ LMTP Handler      │
                            │ (activitypub-lmtp)│
                            └─────────┬────────┘
                                      │ writes
                                      ▼
                              ┌──────────────┐
                              │ Message Queue │
                              └───────┬──────┘
                                      │ picks
                                      ▼
                             ┌──────────────────┐
                             │ Agent Worker      │
                             │  - payload exec   │
                             │  - AI action run  │
                             │  - reply envelope │
                             └─────────┬────────┘
                                       │ SMTP
                                       ▼
                              ┌──────────────────┐
                              │ Agent Reply Flow  │
                              └──────────────────┘
```
---

## 主な機能
### 1. **Envelope メッセージモデル**
AI Agent Hub のすべての操作は Envelope（封筒）として表現されます。

- sender
- recipient
- envelope_type
- payload
- context
- inReplyTo
- created_at
- version

これにより、**AIの行動ログ・状態・結果**をすべてメッセージとして残すことができます。

### 2. **MTAベースのメッセージ配信**
- Postfix が SMTP submission を受け取る
- LMTP handler が JSON envelope を取り出す
- Queue に保存し、Worker が非同期で実行
- 返信（pong など）も同じく MTA 経由で返送

MTA の再送・バッファ機構のおかげで、非常に堅牢な分散処理が可能になります。

### 3. **Agent Worker による AI 実行**
- OpenAI / Local LLM / Function calling 等を自由に差し替え
- Envelope の payload に基づき任意のアクションを実行
- 実行結果は **reply envelope** として再び流す

---

## サーバ構成（標準）
- **OS**: Linux (Amazon Linux / Ubuntu)
- **MTA**: Postfix
- **LMTP**: Dovecot LMTP または独自 handler
- **Queue**: SQLite / PostgreSQL / SQS
- **Worker**: Python または Node.js

AWS無料枠だと：
- EC2 Micro (Postfix + LMTP)
- SQS queue / or local SQLite
- Lambda Worker（も可）

---

## ディレクトリ構成
```
ai-agent-os/
  ├── smtp_sender.py        # Envelope を SMTP 送信
  ├── lmtp_handler.py       # LMTP受信 → Queue 書き込み
  ├── queue/                # SQLite or message queue
  ├── worker/               # AI Worker（LLM実行）
  ├── tests/                # E2E pipeline tests
  ├── docs/                 # 仕様書
  └── README.md
```

---

## end-to-end パイプラインテスト
テストでは以下の流れを自動検証します：

1. SMTP submission（Envelope送信）
2. LMTP handler による受信
3. Queue persistence（保存）
4. Agent Worker 処理
5. Reply Envelope（pong）の送信
6. メッセージID/Thread の整合性チェック

これにより、**AI Action → MTA経由 → AI Action reply** のループが完全に保証されます。

---

## 利用例
### 1. AIアクション処理（Agent → Agent）
- タスク分解
- Web検索
- 計画生成
- API呼び出し
- Notion/CRM 更新

### 2. AIログの永続化
- 全てのAIの行動が Envelope として保存される
- 監査ログやトレースが必ず残る

### 3. ActivityPub連携（拡張モジュール）
- LMTP handler で ActivityStreams JSON を組み立て
- Post/Follow/Inbox 処理

MTAベースSNS（分散SNS OS）への応用が可能

---

## 将来拡張
- Web UI inbox（メールクライアントの様に AI メッセージを閲覧）
- エージェントマーケット（Plugin/Function の共有）
- SQS + Lambda による水平スケール
- AIの行動経路をグラフ化

---

## ライセンス
Apache 2.0（予定）

---

## コントリビュート
Issue/PR 歓迎します。
AI Agent OS を一緒に作りましょう。

