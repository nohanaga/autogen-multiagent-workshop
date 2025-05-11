import logging
from typing import Any, List  
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.teams import Swarm
from autogen_agentchat.conditions import TextMentionTermination, MaxMessageTermination
from autogen_core import CancellationToken

from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools

from autogen.base_agent import BaseAgent

# Define termination condition
termination_condition = TextMentionTermination("TERMINATE:") | MaxMessageTermination(max_messages=10)

class Agent(BaseAgent):
    """
    Simplified multi-agent system using Swarm architecture with 3 agents:
    • Coordinator: Routes requests to specialists
    • Billing Agent: Handles customer accounts and payments
    • Product Agent: Provides information on products and promotions
    """

    def __init__(self, state_store: dict, session_id: str) -> None:
        super().__init__(state_store, session_id)
        self.team_agent = None
        self._initialized = False

    async def _setup_team_agent(self) -> None:
        """Create the swarm team once per session."""
        if self._initialized:
            return

        try:
            # 1. Setup tools
            server_params = SseServerParams(
                url=self.mcp_server_uri,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            # HINT: One approach to improve performance is to specify which tools to use in each agent. That are domain specific.
            tools = await mcp_server_tools(server_params)

            # 2. Setup model client
            model_client = AzureOpenAIChatCompletionClient(
                api_key=self.azure_openai_key,
                azure_endpoint=self.azure_openai_endpoint,
                api_version=self.api_version,
                azure_deployment=self.azure_deployment,
                model=self.openai_model_name,
            )

            # 3. Create simplified agents
            # HINT: You can adjust the prompts to improve the performance. 
            coordinator = AssistantAgent(  
                name="coordinator",  
                model_client=model_client,  
                handoffs=["CRMBillingAgent", "ProductPromotionsAgent"],
                description="タスクを計画するエージェント。ユーザーのリクエストを適切な専門エージェントに振り分けてください。",
                system_message=(  
            """
            あなたはコーディネーターです。ユーザーのリクエストを適切な専門エージェントに振り分けてください。
            質問に直接答えてはいけません。必ず適切なエージェントにルーティングしてください。
            - 請求やアカウント、CRM、SNS分析に関する質問は：CRMBillingAgent に振り分けること
            - 製品やプロモーションに関する質問は：ProductPromotionsAgent に振り分けること
            - 単純な質問に限り、直接回答しても構いません

            # Rule
            - Always send your coordinator first, then handoff to appropriate agent.
            - Always handoff to a single agent at a time.
            - 議論の結果を集約して最終的にユーザーに回答します。
            - 自分は専門エージェントを実行することはできません
            - handoff に失敗したら何度か再実行してください
            - すべての handsoff が終了し、最終回答が完成したら文の最後に TERMINATE: を含めること!

            """
            )
            )  

            billing_agent = AssistantAgent(  
                name="CRMBillingAgent",  
                model_client=model_client,  
                description="CRM & 請求エージェントのエージェント。CRM／請求システムを照会する",
                tools=tools,  
                handoffs=["coordinator"],
                system_message=(
            """
            あなたは「CRM & 請求エージェント（CRM & Billing Agent）」です。

            - アカウント、サブスクリプション、請求書、支払い情報などを取得するために、
            構造化されたCRM／請求システムを照会します。
            - 請求ポリシー、支払い処理、返金ルールなどに関する *ナレッジベース* 記事を確認し、
            回答が正確かつポリシーに準拠していることを保証します。
            - 簡潔で構造化された情報を返答し、検出されたポリシー上の懸念事項があれば
            フラグを立てます。
            - ツールを使って請求情報を確認してください。
            - 請求に関係ない質問は coordinator に振り分けてください。
            - Always handoff back to coordinator when analysis is complete.
            """
                ),  
            )  

            product_agent = AssistantAgent(  
                name="ProductPromotionsAgent",  
                model_client=model_client,  
                handoffs=["coordinator"],
                description="製品 & プロモーションエージェント。プロモーションのオファー、製品の在庫状況、適格条件、割引情報などを照会",
                tools=tools,  
                system_message=(  
            """
            あなたは「製品 & プロモーションエージェント（Product & Promotions Agent）」です。

            - 構造化された情報源から、プロモーションのオファー、製品の在庫状況、
            適格条件、割引情報などを取得します。
            - *ナレッジベース* のFAQ、利用規約、ベストプラクティスを活用して、
            回答を補足します。
            - 事実に基づいた、最新の製品／プロモーション情報を提供します。
            - ツールを使って製品やプロモーションの詳細を確認してください。
            - 製品に関係ない質問は coordinator に振り分けてください。
            - Always handoff back to coordinator when analysis is complete.
            """
                ),  
            )  
            # YOU WILL NEED TO ADD A SECURITY AGENT THAT IS SPECIALIZED IN HANDLING SECURITY RELATED QUESTIONS.
            # security_agent = AssistantAgent(

            participants: List[AssistantAgent] = [  
                coordinator,  
                billing_agent,  
                product_agent
            ]  
            # 4. Create the swarm
            self.team_agent = Swarm(
                participants=participants,
                termination_condition=termination_condition,
            )

            # 5. Restore state if available
            if self.state:
                await self.team_agent.load_state(self.state)

            self._initialized = True

        except Exception as exc:
            logging.error(f"Initialization error: {exc}")
            raise

    async def chat_async(self, prompt: str) -> str:
        await self._setup_team_agent()

        try:
            # Run the conversation
            response = await self.team_agent.run(
                task=prompt,
                cancellation_token=CancellationToken(),
            )

            # Extract the final response
            assistant_response = response.messages[-1].content
            
            # Remove TERMINATE prefix if present
            if "TERMINATE:" in assistant_response:
                assistant_response = assistant_response.replace("TERMINATE:", "").strip()

            # Update chat history
            self.append_to_chat_history([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": assistant_response},
            ])

            # Save state for next turn
            self._setstate(await self.team_agent.save_state())

            return assistant_response

        except Exception as exc:
            logging.error(f"Chat error: {exc}")
            return "Sorry, an error occurred. Please try again."