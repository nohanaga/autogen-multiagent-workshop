# AutoGen Multi-Agent Workshop Setup

このワークショップでは AutoGen を用いて AI エージェントを設計し、実行する方法について説明します。

## Setup & Installation

### 1. Codespaces を起動

GitHub のトップから緑色の「<> Code」ボタンをクリックし、「Create Codespaces on main」ボタンを押下します。

### 2. Install Python dependencies

仮想環境の使用を推奨しますが、Codespaces にはすでに `Python 3.12.x` がインストールされているため、そのままこの Python を使用します。 Python v3.11.x/3.12.x で動作を確認しています。

```bash 
python -V
```

`Python 3.12.x` がすでにインストールされていることを確認します。

```sh
# このファイルが格納されているフォルダーから依存関係をインストールします。
pip install -r agentic_ai/autogen/requirements.txt
```

#### Example `requirements.txt` includes:  
  
- `flask`  
- `faker`  
- `python-dotenv`  
- `tenacity`  
- `openai`  
- `flasgger`  
- `fastmcp`  
- `autogen-ext[mcp,openai,azure]`  
- `autogen-agentchat`  
- `uvicorn`  
- `fastapi`  
- `streamlit`  
- `requests`  
- `pydantic`  
- *(Add others as needed for your specific environment)*  
  
---  

### 3. Deploy LLM model using Azure AI Foundry

1. [ai.azure.com](https://ai.azure.com/) にログインします。アカウントにアクセスできない場合は、アカウントを作成してください。
2. プロジェクトを作成します。既存のハブがない場合は新しいハブを作成します。これにより、ハブ、プロジェクト コンテナ、AI サービス、ストレージ アカウント、および Key Vault が設定されます。
3. API キー、Azure OpenAI Service エンドポイント、およびプロジェクト接続文字列を `.env` ファイルに追加します（次の手順）。
4. プロジェクトページで、［モデル + エンドポイント］ -> ［モデルを展開］ -> ［ベースモデルを展開］ -> ［gpt-4.1］ を選択します。
5. 展開タイプ（Standard、Global Standard など）と地域（必要に応じて）を選択します。
6. 展開の詳細をカスタマイズし、分あたりのトークン数を 10K に減らし、動的クォータを無効にします。
  
  
### 4. 環境変数を設定し、実行するエージェントを選択
  
`.env.sample` を `.env` にリネームし、必要なすべてのフィールドを入力してください：
  
```bash  
#User to replace your-openai-service-endpoint with their model project deployment in Azure AI Foundry
#e.g. https://my-ai-services98765432111.openai.azure.com/
AZURE_OPENAI_ENDPOINT="https://your-openai-service-endpoint.openai.azure.com"

#User to replace your-openai-api-key with their project API Key in Azure AI Foundry
AZURE_OPENAI_API_KEY="your-openai-api-key"

#User to replace model name deployed in foundry if different from gpt-4o
AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4.1"

#User to replace model version deployed in foundry if different from below
AZURE_OPENAI_API_VERSION="2025-03-01-preview"
OPENAI_MODEL_NAME="gpt-4.1"

#User should not need to change the MCP and backend server URLs unless these are not available on your local environment
BACKEND_URL="http://localhost:7000"
MCP_SERVER_URI="http://localhost:8000/sse"

# Specify your agent Python module path  
# AGENT_MODULE="agents.autogen.single_agent.loop_agent"
AGENT_MODULE="path_to_your_agent_module"

# PostgreSQL connection details
PGHOST="your-postgresql-service.postgres.database.azure.com"
PGUSER="user"
PGPORT="5432"
PGDATABASE="database"
PGPASSWORD="Password"

# MongoDB connection string
MONGODB_CONNECTION_STRING="mongodb://"
```

**Note:**    
- Azure リソースが、正しいモデル展開名、エンドポイント、および API バージョンを使用するように構成されていることを確認してください。 
  

### 5. Run MCP Server 

```agentic_ai/backend_services``` フォルダーに移動し、仮想環境が有効化されたターミナルウィンドウで、MCP サーバーを実行します。

```bash
cd agentic_ai/backend_services
python mcp_service.py  
# このターミナルを閉じてはいけません。次の手順のために別のターミナルを開いてください。 
```

MCP サーバーが正常に起動したら、コンソール右上の「＋」ボタンを押下することで新しいターミナルを起動することができます。

![img](docs\img\002.png)

---  
## Tracing and Observability
AutoGen には、アプリケーションの実行に関する包括的な記録を収集するためのトレースと観測のサポートが組み込まれています。この機能は、デバッグ、パフォーマンス分析、そしてアプリケーションのフローを理解するのに役立ちます。

この機能は OpenTelemetry ライブラリを活用しているため、OpenTelemetry と互換性のある任意のバックエンドを使用してトレースを収集および分析できます。

トレースを収集して表示するには、テレメトリバックエンドを設定する必要があります。Jaeger、Zipkinなど、いくつかのオープンソースのオプションが利用可能です。この例では、テレメトリバックエンドとして [Jaeger](https://www.jaegertracing.io/download/) を使用します。
すぐに始めるには、Docker Compose を使用して Jaeger をローカルで実行できます。

```bash
cd jaeger
mkdir esdata
sudo chown -R 1000:1000 ./esdata
docker compose up -d
```

Jaeger ローカルサーバーの起動後、[http://localhost:16686](http://localhost:16686) にアクセスして Jaeger UI を開きます。以下のように「ポート」タブをクリックし、ポート `16686` の転送されたアドレスの「🌐」アイコンをクリックしてブラウザを起動します。

![img](docs\img\003.png)

このように Jaeger UI が表示されれば完了です。

![img](docs\img\004.png)

---  
## Run application(お土産)
```agentic_ai/applications```

共通のバックエンドアプリケーションは、`.env` ファイルで選択されたエージェントを実行し、フロントエンド UI に接続します。
  
### Option 1: バックエンドとフロントエンドを同時に実行する  
  
```bash  
bash run_application.sh  
```
このスクリプトは、FastAPI バックエンド（`backend.py`）と Streamlit フロントエンド（`frontend.py`）を同時に起動します。

- バックエンドは [http://localhost:7000](http://localhost:7000) でリッスンします。
- Streamlit ユーザーインターフェースが開きます（通常は [http://localhost:8501](http://localhost:8501) で開きます）。

### Option 2: バックエンドとフロントエンドを別々に実行する

### 1. Start the FastAPI Backend  
  
```bash  
python backend.py  
# このターミナルを開いたままにしておいてください。フロントエンド用に別のターミナルを開いてください。 
```
バックエンドは `http://localhost:7000/chat` で利用可能です。 

### 2. Start the Streamlit Frontend  
  
```bash  
streamlit run frontend.py  
```
Streamlit が提供するアドレス（通常は http://localhost:8501 ）にアクセスし、チャットインターフェースを使用します。
Streamlit は、エージェント用のチャットウィンドウを新しい Edge タブにポップアップ表示します。

すべてのステップを正常に完了した場合、設定は完了し、エージェントが現在実行中です！


## How It Works  
  
1. **Web UI （Streamlit）：**
ユーザーがメッセージを入力し、アシスタントとやり取りします。各チャットセッションごとに一意のセッションIDが生成されます。
2. **バックエンド （FastAPI）：**
ユーザーのプロンプトを受信し、セッションとメモリ内のチャット履歴を管理し、環境設定に応じてエージェントを取得または作成します。
3. **エージェント （AGENT_MODULE で指定）：**    
   Azure OpenAI とオプションの MCP ツールを使用して入力を処理します。エージェントは、設定に応じて単一エージェント、マルチエージェント、または協働モードで動作します。
4. **チャット履歴：**
会話履歴はセッションごとに保存され、フロントエンドに表示したり、必要に応じてリセットしたりできます。 
  
---  
  
## FastAPI Endpoints  
  
- `POST /chat`    
  Send a JSON payload with `{ "session_id": ..., "prompt": ... }`. Returns the assistant’s response.  
  
- `POST /reset_session`    
  Send a payload `{ "session_id": ... }` to clear the conversation history for that session.  
  
- `GET /history/{session_id}`    
  Fetches all previous messages for a given session.  
  


---  
## Notes & Best Practices  
  
- 現在のセッションストアはメモリ内のPython辞書を使用しています。本番環境へのデプロイ時には、Redisやデータベースなどの永続化ストアに置き換えてください。 
- `.env` ファイル内のシークレット（API キーなど）は、バージョン管理にコミットしないようにしてください。
- MCP サーバーと Azure エンドポイントの URL は、バックエンドからアクセス可能である必要があります。
- 異なるエージェントの動作を実験するには、`.env` 内の `AGENT_MODULE` を調整してください。 

---

## Acknowledgments  
  
- https://github.com/microsoft/OpenAIWorkshop
- MCP Project    
- AutoGen