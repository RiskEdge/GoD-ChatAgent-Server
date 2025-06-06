from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough

from .logs.logger import setup_logger
import os

logger = setup_logger("GoD AI Chatbot: Agent Setup", "app.log")

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
    Ask clear, focused questions one at a time
    Use straightforward, professional language
    Thank users for providing information
    Summarize collected information for confirmation
    Stay focused on information gathering rather than problem-solving

Process:
    Greet the user and ask for their issue description
    Systematically gather device and problem details
    Ask follow-up questions to clarify specifics
    Provide a structured summary of all collected information
    Confirm accuracy of the summary with the user

If users ask for help beyond information gathering:

Politely redirect: "I am here to gather information about your device issue. Could you tell me more about [relevant detail]?"
Stay focused on collecting the missing information.

Your success is measured by how thoroughly and accurately you can document the users technical issue and device information.

You will also be provided with the conversation history.
"""

class ChatAssistantChain:
    def __init__(self, callback_handler=None):
        self.memory = ConversationBufferMemory(return_messages=True)
        self.callback_handler = callback_handler
        self.llm = ChatOpenAI(
            model="o3-mini", 
            max_tokens=2000, 
            streaming=True,
            callbacks=[self.callback_handler] ,
        )
        self.prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", SYS_PROMPT),
                    MessagesPlaceholder(variable_name="history"),
                    ("human", "{input}"),
                ]
            )
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
            self.prompt
                |
            self.llm
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
            logger.info(f"AI response: {response.content}")
            
            self.memory.save_context({"input": user_input}, {"output": response.content})
            logger.info("Memory updated.")
            return response.content
        except Exception as e:
            logger.error(f"Error during chain execution: {e}")
            return None