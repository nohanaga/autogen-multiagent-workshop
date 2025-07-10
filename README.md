# AutoGen Multi-Agent Workshop
  
AutoGen Multi-Agent Workshop の公式リポジトリへようこそ！このリポジトリでは、Microsoft の先進的な AI 技術を活用して、エージェントベースの AI ソリューションを調査、プロトタイピング、比較するための必要なリソース、コード、ドキュメントをすべて提供しています。 


---  
  
## このワークショップでできること
  
- **現実のビジネスシナリオ向けのエージェントソリューションの設計とプロトタイピング**
- **単一エージェントとマルチエージェントのアーキテクチャおよびアプローチの比較**
- **異なるプラットフォームを使用してエージェントの実装を開発し、比較する**
  - ~~Azure AI Agent Service~~
  - ~~Semantic Kernel~~
  - Autogen  
  
---  
  
## Key Features  
  
- **設定可能なLLMバックエンド：** 最新の Azure OpenAI GPT モデル（例： GPT-4.1、GPT-4o）を使用できます。
- **MCPサーバー統合：** エージェントのオーケストレーションと機能を強化する高度なツールを提供します。
- **柔軟なエージェントアーキテクチャ：**
- 単一エージェント、マルチエージェント、またはリフレクションベースのエージェントをサポート（`.env`で選択可能）。 
  - エージェントは、モジュールで定義された動的な役割を実行するために、自己ループ、協力、リフレクションを行うことができます。
- **セッションベースのチャット：** 各セッションごとの永続的な会話履歴。
- **フルスタックアプリケーション：**  
  - FastAPI バックエンドと RESTful エンドポイント（チャット、リセット、履歴など）。
- Streamlit フロントエンドによるリアルタイムチャット、セッション管理、履歴表示。
- **環境ベースの構成：** `.env`ファイルを使用してシステムを簡単に構成できます。 
  
---  
  
## Getting Started  
  
環境要件と手順ごとのインストール手順を確認するには、[セットアップ手順](./SETUP.md) を参照してください。 GitHub Codespages を使用される方は[こちら](./SETUP_Codespaces.md)。

---  
  
## AutoGen Notebooks
### Single Agent
- [Loop Agent](agentic_ai/autogen/single_agent/loop_agent.ipynb)
- [Memory and RAG](agentic_ai/autogen/single_agent/memory.ipynb)
### Multi Agent
- [Round Robin Group](agentic_ai/autogen/multi_agent/collaborative_multi_agent_round_robin.ipynb)
- [Selector Group](agentic_ai/autogen/multi_agent/collaborative_multi_agent_selector_group.ipynb)
- [Swarm](agentic_ai/autogen/multi_agent/handoff_multi_domain_agent.ipynb)
- [Magentic-One](agentic_ai/autogen/multi_agent/magentic-one_agent.ipynb)
- [Reflection](agentic_ai/autogen/multi_agent/reflection_agent.ipynb)
- [GraphFlow](agentic_ai/autogen/multi_agent/graphflow_agent.ipynb)
- [GraphFlow Advanced](agentic_ai/autogen/multi_agent/graphflow_agent_advanced.ipynb)



## License  
  
This project is licensed under the terms described in the [LICENSE](./LICENSE) file.  
  
---  