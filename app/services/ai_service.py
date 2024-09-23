from langchain import hub
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import build_resource_service
from app.config import OPENAI_API_KEY

class AIService:
    def __init__(self, credentials, instructions):
        self.api_resource = build_resource_service(credentials=credentials)
        self.toolkit = GmailToolkit(api_resource=self.api_resource)
        self.tools = self.toolkit.get_tools()

        base_prompt = hub.pull("langchain-ai/openai-functions-template")
        prompt = base_prompt.partial(instructions=instructions)

        llm = ChatOpenAI(temperature=0, model="gpt-4o-mini", api_key=OPENAI_API_KEY)
        agent = create_openai_functions_agent(llm, self.tools, prompt)

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=False,
        )

    def generate_response(self, email_data):
        response = self.agent_executor.invoke(email_data)
        return response['output']
