import logging  
from typing import Any, List  
  
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.teams import SelectorGroupChat  # keeps implementation simple & familiar  
from autogen_agentchat.conditions import TextMessageTermination,TextMentionTermination,MaxMessageTermination 
from autogen_core import CancellationToken  
  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  
  
from autogen.base_agent import BaseAgent  
  
selector_prompt = """Select an agent to perform task.

{roles}

Current conversation context:
{history}

Read the above conversation, then select an agent from {participants} to perform the next task.
Make sure the planner agent has assigned tasks before other agents start working.
Only select one agent.
"""
text_mention_termination = TextMentionTermination("TERMINATE")
max_messages_termination = MaxMessageTermination(max_messages=25)
termination_condition = text_mention_termination | max_messages_termination


class Agent(BaseAgent):  
    """  
    Collaborative multi‑agent system composed of:  
        • Analysis & Planning Agent (orchestrator)  
        • CRM & Billing Agent  
        • Product & Promotions Agent  
        • Security & Authentication Agent  
  
    Each specialist has access to the central Knowledge Base through the  
    mcp_server_tools tool‑suite.  The Analysis & Planning Agent orchestrates  
    the conversation and produces the final answer.  
  
    Conversations finish when the Analysis & Planning Agent sends its  
    synthesis (TextMessageTermination("analysis_planning")).  
    """  
  
    def __init__(self, state_store: dict, session_id: str) -> None:  
        super().__init__(state_store, session_id)  
        self.team_agent: Any = None  
        self._initialized: bool = False  
  
    # --------------------------------------------------------------------- #  
    #                         TEAM INITIALISATION                           #  
    # --------------------------------------------------------------------- #  
    async def _setup_team_agent(self) -> None:  
        """Create/restore the collaborative team once per session."""  
        if self._initialized:  
            return  
  
        try:  
            # 1. -----------------  Shared Tooling (Knowledge Base access)  -----------------  
            server_params = SseServerParams(  
                url=self.mcp_server_uri,  
                headers={"Content-Type": "application/json"},  
                timeout=30,  
            )  
            tools = await mcp_server_tools(server_params)  
  
            # 2. -----------------  Shared Model Client -----------------  
            model_client = AzureOpenAIChatCompletionClient(  
                api_key=self.azure_openai_key,  
                azure_endpoint=self.azure_openai_endpoint,  
                api_version=self.api_version,  
                azure_deployment=self.azure_deployment,  
                model=self.openai_model_name,  
            )  
  
            # 3. -----------------  Agent Definitions -----------------  
            analysis_planning_agent = AssistantAgent(  
                name="AnalysisPlanningAgent",  
                model_client=model_client,  
                description="タスクを計画するエージェント。新しいタスクが与えられたときに最初に起動するエージェントであるべきである。",
                system_message=(  
            """
            あなたは「分析 & 計画エージェント（Analysis & Planning Agent）」です – 全体のオーケストレーターとして機能します。

            あなたの役割:
            1) 顧客からの抽象的なリクエストを解析すること。
            2) リクエストを明確なサブタスクに分解し、それぞれを専門エージェント
            （crm_billing、product_promotions）に割り当てること。
            3) 各専門エージェントからの出力を統合し、1つの包括的で一貫性のある
            顧客向けの回答としてまとめること。
            4) 満足のいく結果が得られたら、以下のプレフィックスを付けて顧客に最終回答すること
            TERMINATE

            まだ情報が不足している場合は、専門エージェントとの対話を継続してください。
            情報が揃っていれば調査結果を要約し、文の最後に TERMINATE を含めること!

            """
            )
            )  

            crm_billing_agent = AssistantAgent(  
                name="CRMBillingAgent",  
                model_client=model_client,  
                description="CRM & 請求エージェントのエージェント。CRM／請求システムを照会する",
                tools=tools,  
                system_message=(
            """
            あなたは「CRM & 請求エージェント（CRM & Billing Agent）」です。

            - アカウント、サブスクリプション、請求書、支払い情報などを取得するために、
            構造化されたCRM／請求システムを照会します。
            - 請求ポリシー、支払い処理、返金ルールなどに関する *ナレッジベース* 記事を確認し、
            回答が正確かつポリシーに準拠していることを保証します。
            - 簡潔で構造化された情報を返答し、検出されたポリシー上の懸念事項があれば
            フラグを立てます。
            """
                ),  
            )  

            product_promotions_agent = AssistantAgent(  
                name="ProductPromotionsAgent",  
                model_client=model_client,  
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
            """
                ),  
            )  

            data_analyst_agent = AssistantAgent(  
                name="DataAnalystAgent",  
                description="データに基づいて分析、計算、集計を行うためのエージェント。",
                model_client=model_client,  
                system_message=(
            """
            あなたはデータアナリストです。
            割り当てられたタスクに基づき、提供されたツールを使用してデータを分析し、結果を提供してください。
            データを確認していない場合は、要求してください。
            """
                ),  
            )  
            
            # 4. -----------------  Assemble Team -----------------  
            participants: List[AssistantAgent] = [  
                    crm_billing_agent,  
                    product_promotions_agent,  
                    analysis_planning_agent,       # orchestrator always concludes a cycle  
            ]  
  
  
            self.team_agent = SelectorGroupChat(  
                participants=participants,  
                termination_condition=termination_condition, 
                selector_prompt=selector_prompt,
                model_client=model_client,
                allow_repeated_speaker=True,  # Allow an agent to speak multiple turns in a row.
 
            )  
  
            # 5. -----------------  Restore persisted state (if any) -----------------  
            if self.state:  
                await self.team_agent.load_state(self.state)  
  
            self._initialized = True  
  
        except Exception as exc:  
            logging.error(f"[MultiDomainAgent] Initialisation failure: {exc}")  
            raise  # re‑raise so caller is aware something went wrong  
  
    # --------------------------------------------------------------------- #  
    #                              CHAT ENTRY                               #  
    # --------------------------------------------------------------------- #  
    async def chat_async(self, prompt: str) -> str:  
        """  
        Executes the collaborative multi‑agent chat for a given user prompt.  
  
        Returns  
        -------  
        str  
            The final, synthesised reply produced by the Analysis & Planning Agent.  
        """  
        await self._setup_team_agent()  
  
        try:  
            response = await self.team_agent.run(  
                task=prompt,  
                cancellation_token=CancellationToken(),  
            )  
  
            assistant_response: str = response.messages[-1].content  
            assistant_response = assistant_response.replace("FINAL_ANSWER:", "").strip()
  
            # Persist interaction in chat history so UI / analytics can render it.  
            self.append_to_chat_history(  
                [  
                    {"role": "user", "content": prompt},  
                    {"role": "assistant", "content": assistant_response},  
                ]  
            )  
  
            # Persist internal Agent‑Chat state for future turns / resumptions.  
            new_state = await self.team_agent.save_state()  
            self._setstate(new_state)  
  
            return assistant_response  
  
        except Exception as exc:  
            logging.error(f"[MultiDomainAgent] chat_async error: {exc}")  
            return (  
                "Apologies, an unexpected error occurred while processing your "  
                "request.  Please try again later."  
            )  