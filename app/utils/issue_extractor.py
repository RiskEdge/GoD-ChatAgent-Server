from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from ..models.user_issue_model import UserIssueBase
from ..logs.logger import setup_logger

logger = setup_logger("GoD AI Chatbot: Issue Extractor", "app.log")

class IssueExtractor:
    def __init__(self):
        self.llm = ChatOpenAI(model="o4-mini")
        self.parser = JsonOutputParser(pydantic_object=UserIssueBase)
        self.prompt = ChatPromptTemplate.from_template(
            """
            You are an expert data extraction agent. Your task is to analyze a conversation transcript between a support agent and a user and extract the required information into a JSON object.
            
            Analyze the following transcript:
            ---
            {transcript}
            ---
            Based on the transcript, extract the device details, purchase information, and problem description. Also, create a final summary of the user's issue. If a piece of information is missing, use `null`.

            {format_instructions}
            """
        )
        self.chain = self.prompt | self.llm | self.parser
        
    async def extract_issue_details(self, transcript: str, user_id: str, conversation_id: str) -> dict:
        try:
            format_instructions = self.parser.get_format_instructions()
            logger.info(f"Extracting issue details from transcript: {transcript}")
            response = await self.chain.ainvoke({"transcript": transcript, "format_instructions": format_instructions})
            logger.info(f"Extracted issue details: {response}")
            response['user_id'] = user_id
            response['conversation_id'] = conversation_id
            return response
        except Exception as e:
            logger.error(f"Error extracting issue details: {e}")
            raise e
