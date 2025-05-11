import os  
from dotenv import load_dotenv  
  
from autogen_agentchat.agents import AssistantAgent  
from autogen_agentchat.teams import RoundRobinGroupChat  
from autogen_agentchat.conditions import TextMessageTermination  
from autogen_core import CancellationToken  
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient  
from autogen_ext.tools.mcp import SseServerParams, mcp_server_tools  
  
from autogen.base_agent import BaseAgent    
load_dotenv()  
  
class Agent(BaseAgent):  
    def __init__(self, state_store, session_id) -> None:  
        super().__init__(state_store, session_id)  
        self.loop_agent = None  
        self._initialized = False  
  
    async def _setup_loop_agent(self) -> None:  
        """Initialize the assistant and tools once."""  
        if self._initialized:  
            return  
  
        server_params = SseServerParams(  
            url=self.mcp_server_uri,  
            headers={"Content-Type": "application/json"},  
            timeout=30  
        )  
  
        # Fetch tools (async)  
        tools = await mcp_server_tools(server_params)  
  
        # Set up the OpenAI/Azure model client  
        model_client = AzureOpenAIChatCompletionClient(  
            api_key=self.azure_openai_key,  
            azure_endpoint=self.azure_openai_endpoint,  
            api_version=self.api_version,  
            azure_deployment=self.azure_deployment,  
            model=self.openai_model_name,  
        )  
  
        # Set up the assistant agent  
        agent = AssistantAgent(  
            name="ai_assistant",  
            model_client=model_client,  
            tools=tools,  
            system_message=(  
                "あなたは役立つアシスタントです。複数のツールを使用して情報を検索し、質問に回答することができます。"  
                "利用可能なツールを確認し、必要に応じて使用してください。ユーザーが不明点がある場合は、確認のための質問をすることもできます。"
            )
        )  
  
        # Set the termination condition: stop when agent answers as itself  
        termination_condition = TextMessageTermination("ai_assistant")  
  
        self.loop_agent = RoundRobinGroupChat(  
            [agent],  
            termination_condition=termination_condition,  
        )  
  
        if self.state:  
            await self.loop_agent.load_state(self.state)  
        self._initialized = True  
  
    async def chat_async(self, prompt: str) -> str:  
        """Ensure agent/tools are ready and process the prompt."""  
        await self._setup_loop_agent()  
  
        response = await self.loop_agent.run(task=prompt, cancellation_token=CancellationToken())  
        assistant_response = response.messages[-1].content  
  
        messages = [  
            {"role": "user", "content": prompt},  
            {"role": "assistant", "content": assistant_response}  
        ]  
        self.append_to_chat_history(messages)  
  
        # Update/store latest agent state  
        new_state = await self.loop_agent.save_state()  
        self._setstate(new_state)  
  
        return assistant_response  