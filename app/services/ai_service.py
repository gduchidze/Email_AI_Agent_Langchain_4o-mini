from langchain import hub
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI
from langchain_community.agent_toolkits import GmailToolkit
from langchain_community.tools.gmail.utils import build_resource_service
from app.config import OPENAI_API_KEY
from app.services.gmail_services import GmailSendMessage, GmailGetMessage, GmailGetThread


class AIService:
    def __init__(self, credentials, instructions):
        self.api_resource = build_resource_service(credentials=credentials)
        self.toolkit = GmailToolkit(api_resource=self.api_resource)
        self.tools = self.toolkit.get_tools() + [
            GmailSendMessage(api_resource=self.api_resource),
            GmailGetMessage(api_resource=self.api_resource),
            GmailGetThread(api_resource=self.api_resource)
        ]

        base_prompt = hub.pull("langchain-ai/openai-functions-template")
        formatting_instructions = """
        When formatting your email response, follow these rules:
        1. Start with a proper salutation, e.g., "Dear [Name]," or "Hello [Name],"
        2. Use HTML tags for formatting:
           - <p> for paragraphs
           - <ul> and <li> for unordered lists
           - <ol> and <li> for ordered lists
           - <strong> for bold text
           - <em> for italic text
        3. Use line breaks <br> when appropriate
        4. End with a polite sign-off, e.g., "<p>Best regards,<br>[Your Name]</p>"
        5. Wrap the entire response in a <div> tag

        Example format:
        <div>
        <p>Dear [Name],</p>

        <p>Thank you for your inquiry about [topic]. I'm happy to provide you with the information you need.</p>

        <p>Here are the details you requested:</p>
        <ul>
          <li><strong>Point 1</strong>: [Details]</li>
          <li><strong>Point 2</strong>: [Details]</li>
          <li><strong>Point 3</strong>: [Details]</li>
        </ul>

        <p>If you need any further clarification, please don't hesitate to ask. We're here to assist you.</p>

        <p>Best regards,<br>[Your Name]</p>
        </div>
        """
        full_instructions = instructions + "\n\n" + formatting_instructions
        prompt = base_prompt.partial(instructions=full_instructions)
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