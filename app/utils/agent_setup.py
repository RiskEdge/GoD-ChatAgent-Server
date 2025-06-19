from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from pydantic import BaseModel
from typing import Optional, List

from ..logs.logger import setup_logger

class AgentResponse(BaseModel):
    response: str
    options: Optional[List] = None


logger = setup_logger("GoD AI Chatbot: Agent Setup", "app.log")
parser = JsonOutputParser(pydantic_object=AgentResponse)

SYS_PROMPT="""You are a technical support agent whose role is to gather comprehensive information about device issues through structured conversation. You do not troubleshoot or resolve problems - your goal is to collect detailed information about the user's device and technical issue.
Always keep you messages crisp and short.

Information to Collect:
    Device Details:
        Brand and exact model
        Device type and specifications
        Operating system/software version

    Purchase Information:
        Purchase date
        Warranty status and duration
        Purchase location if relevant

    Problem Description:
        Specific symptoms and error messages
        When the issue occurs (patterns, frequency)
        What triggers the problem
        Previous troubleshooting attempts

Communication Guidelines:
    Ask clear, focused questions only one at a time
    Instead of giving examples in the response, give them as options.
    Use straightforward, professional language
    Provide options only when context-appropriate (e.g., device types, frequency patterns,possible issues, yes/no questions, etc.)
    Summarize all collected information before confirmation
    Stay focused on information gathering rather than problem-solving
    

Process:
    Greet the user and ask for their issue description with options(if applicable)
    Systematically gather device and problem details
    Ask follow-up questions(with proper options if applicable) to clarify specifics
    Provide a structured summary of all collected information
    Confirm accuracy of the summary with the user. Your question for this MUST be exactly: "I have gathered all the necessary information. Is this summary correct?"

If users ask for help beyond information gathering:
Politely redirect: "I am here to gather information about your device issue. Could you tell me more about [relevant detail]?"
Stay focused on collecting the missing information.

Your success is measured by how thoroughly and accurately you can document the users technical issue and device information.

You MUST format your response as JSON using the following structure:
{format_instructions}

Response Field: Contains your question or statement to the user.
Options Field: Contains 3-5 relevant answer choices when appropriate

Have a look at the examples below to see what kind of options are appropriate based on the issue/device:
For device brand: {{ {{"response"}}: "What brand is your device?", {{"options"}}: ["Apple", "Samsung", "Dell", "HP", "Other"]}}
For problem frequency:{{ {{"response"}}: "How often does this issue occur?", {{"options"}}: ["Every time", "Several times a day", "Once a day", "Occasionally", "Other"] }}
For confirmation: {{ {{"response"}}: "I have gathered all the necessary information. Is this summary correct?", {{"options"}}: ["Yes", "No - needs correction"]}}

You will be provided with conversation history to understand what information has already been collected.
"""

class ChatAssistantChain:
    def __init__(self, callback_handler=None):
        self.memory = ConversationBufferMemory(return_messages=True)
        self.callback_handler = callback_handler
        self.llm = ChatOpenAI(
            model="o4-mini", 
            # max_tokens=2000, 
            # streaming=True,
            # callbacks=[self.callback_handler] ,
        )
        self.prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", SYS_PROMPT),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}"),
                ]
            )
        self.partial_prompt = self.prompt.partial(format_instructions=parser.get_format_instructions())
        logger.info("ChatAssistantChain initialized.")

    def get_memory_messages(self, query):
        try:
            history = self.memory.load_memory_variables(query).get("history", [])
            logger.debug(f"Loaded memory history:\n {history}\n\n")
            return history
        except Exception as e:
            logger.error(f"Error loading memory history: {e}")
            return []
    
    def get_chain(self):
        try:
            chain = (
                RunnablePassthrough.assign(
                    history=RunnableLambda(self.get_memory_messages)
                )
                |
            self.partial_prompt
                |
            self.llm
                |
            parser
            )
            logger.info("Chain initialized.")
            return chain
        except Exception as e:
            logger.error(f"Error initializing chain: {e}")
            raise
        
    async def run(self, user_input):
        try:
            chain = self.get_chain()
            logger.info(f"Processing user input: {user_input}")
            response = await chain.ainvoke({"input": user_input})
            logger.info(f"AI response: {response}")
            
            self.memory.save_context({"input": user_input}, {"output": response["response"]})
            logger.info("Memory updated.")
            return response
        except Exception as e:
            logger.error(f"Error during chain execution: {e}")
            return None