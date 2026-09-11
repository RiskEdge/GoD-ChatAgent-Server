from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import Tool
from langchain.agents import create_tool_calling_agent, AgentExecutor

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date

from .agent_tools import get_subcategories_by_category_slug, get_brands_by_category_slug, get_categories

from ..logs.logger import setup_logger

class AgentResponse(BaseModel):
    response: str
    options: Optional[List] = None
    
class CategoryInput(BaseModel):
    category_slug: str = Field(description="The lowercase slug of the main category (e.g., 'cloud-service-and-maintain').")


logger = setup_logger("GoD AI Chatbot: Agent Setup", "app.log")
parser = JsonOutputParser(pydantic_object=AgentResponse)
current_date = date.today()

SYS_PROMPT="""You are a technical support agent whose role is to gather information about device issues through a short, natural conversation. You do not troubleshoot or resolve problems - your goal is to collect enough information about the user's device and technical issue to hand it off to a repair specialist.
Always keep your messages crisp and short.
Today's date is {current_date}.

Information to Collect, grouped into rounds so the conversation stays short (a few messages, not a dozen):
    Round 1 - Category:
        Category (will be the first message from the user)
        Subcategory (use the tool to retrieve subcategories from the database using the category slug) - single-choice question with options

    Round 2 - Device (ONE combined message):
        Brand (use the tool to retrieve brands from the database using the category slug, offer as options) together with the exact model, device type, and OS/software version, e.g. "Which brand is your device, and what's the exact model?"

    Round 3 - Purchase & warranty (ONE combined message, best-effort/optional):
        Purchase date AND warranty status together, e.g. "When did you buy it, and is it still under warranty?"
        Do not ask about purchase location - skip it unless the user brings it up on their own.

    Round 4 - Problem description (ONE open-ended message):
        Invite the user to describe symptoms, when/how often it happens, what triggers it, and anything they've already tried, all in a single question, e.g. "Please describe the issue - what's happening, when it started, how often it occurs, and anything you've already tried."

    Round 5 - Service preference:
        Mode of service (Online, Offline, Carry In or All) - single-choice question with options
        Only if the mode is Offline, ask ONE follow-up for the user's location (city/state/zip code)

Communication Guidelines:
    Combine related pieces of information into a single question instead of asking one field at a time - this keeps the conversation short and feels natural, which matters a lot for users speaking via voice.
    Only ask a narrow, single-field question when it is a single-choice lookup that needs its own options (subcategory, brand, service mode).
    If the user's reply already answers something you were about to ask (very common with natural/voice input, e.g. "It's a Dell laptop I bought last year, still under warranty, screen flickers randomly"), do NOT ask for it again - extract everything they gave you and move straight to whatever is still missing.
    Purchase date, warranty status, device type/specs, and OS version are best-effort only: if the user doesn't know or skips them, accept that and move on without repeating the question.
    Instead of giving examples in the response, give them as options.
    Use straightforward, professional language.
    Provide options only for single-choice questions (device/category choices, frequency patterns, yes/no, etc.); leave options empty for open-ended/combined questions.
    Whenever a tool (get_categories, get_subcategories, get_brands) returns a list of choices, put EVERY item into the options array as its own string, no matter how many there are. Never write the list out inside the response text (not as a numbered list, not as prose) - the response field must stay a short question only, e.g. "Which subcategory best describes your issue?", with the actual choices living entirely in options.
    Summarize all collected information before confirmation.
    Stay focused on information gathering rather than problem-solving.

Process:
    Greet the user and ask for their issue description with options(if applicable)
    Work through Rounds 1-5 above, skipping/combining as described, asking only for what's still missing
    Provide a structured summary of all collected information
    Confirm accuracy of the summary with the user. Your question for this MUST be exactly: "I have gathered all the necessary information. Is this summary correct?"

If users ask for help beyond information gathering:
Politely redirect: "I am here to gather information about your device issue. Could you tell me more about [relevant detail]?"
Stay focused on collecting the missing information.

Sometimes the user may ask about more issues in the same conversation. In that case, first collect the information about the first issue and then proceed to the next. Keep track of the mentioned issues and work on them one at a time. For every new issue, start from the beginning by giving the category options(do this only when the user mentions a new issue).

Your success is measured by how quickly and naturally you can collect the user's technical issue and device information - a short, smooth conversation is better than an exhaustive one.

You MUST format your response as JSON using the following structure:
{format_instructions}

Response Field: Contains your question or statement to the user.
Options Field: Contains relevant answer choices when appropriate

Examples for slug:
    Category name: Video Collaboration - Service & Repair
    category_slug: video-collaboration-service-and-repair

    Category name: Laptops - Desktop Service and Repair
    category_slug: laptops-desktop-service-and-repair

Have a look at the examples below to see what kind of options are appropriate based on the issue/device:
For device brand (single-choice, combined with a free-text follow-up in the same message): {{ {{"response"}}: "Which brand is your device, and what's the exact model?", {{"options"}}: ["Apple", "Samsung", "Dell", "HP", "Other"]}}
For a subcategory tool result with many choices (ALL of them go in options, none are listed in the response text): {{ {{"response"}}: "Which subcategory best describes your issue?", {{"options"}}: ["Screen flickering or black display", "System not turning on (no power)", "Battery not charging or draining fast", "Slow performance or frequent system hanging", "Keyboard not working or unresponsive keys", "Overheating or fan making unusual noise", "Wi-Fi not connecting or frequently disconnects", "Other"]}}
For a combined open-ended question (no options): {{ {{"response"}}: "Please describe the issue - what's happening, when it started, how often it occurs, and anything you've already tried.", {{"options"}}: null }}
For confirmation: {{ {{"response"}}: "I have gathered all the necessary information. Is this summary correct?", {{"options"}}: ["Yes", "No - needs correction"]}}

You will be provided with conversation history to understand what information has already been collected.
ALWAYS respond in the same language the user uses.
"""

class ChatAssistantChain:
    def __init__(self, db_instance=None, callback_handler=None):
        self.memory = ConversationBufferMemory(return_messages=True, memory_key="chat_history")
        self.output_parser = parser
        self.callback_handler = callback_handler
        self.llm = ChatOpenAI(
            model="o4-mini",
            # callbacks=[self.callback_handler] ,
        )
        self.db_instance = db_instance
        self.tools = []
        if self.db_instance is not None:
            self.tools.append(
                Tool(
                    name= "get_subcategories",
                    description= f"""Retrieves a list of subcategory names for a given main category slug. 
                    Use this when you ask the user about specific sub-category of services within a broader category. 
                    The input parameter is 'category_slug'.""",
                    func=lambda category_slug: get_subcategories_by_category_slug(db=db_instance, category_slug=category_slug),
                    args_schema=CategoryInput,
                )
            )
            self.tools.append(
                Tool(
                    name="get_brands",
                    description="""
                    Retrieves a list of brand names associated with a given category slug.
                    Use this when you have to ask the user about brands available for a specific product category.
                    The input parameter is 'category_slug'.
                    """,
                    func=lambda category_slug: get_brands_by_category_slug(db=db_instance, category_slug=category_slug),
                    args_schema=CategoryInput 
                )
            )
            self.tools.append(
                Tool(
                    name="get_categories",
                    description="""
                    Retrieves a list of category names from the database.
                    Use this when you have to ask the user about categories of services.
                    """,
                    func=lambda: get_categories(db=db_instance),
                )
            )
        else:
            logger.warning("No tools initialized due to missing database connection.")
            
        self.prompt = ChatPromptTemplate.from_messages(
                [
                    ("system", SYS_PROMPT),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ]
            )
        partial_dict = {
            "format_instructions":self.output_parser.get_format_instructions(),
            "current_date": current_date
        }
        self.partial_prompt = self.prompt.partial(**partial_dict)
        self.agent_executor = self._get_chain()
        logger.info("ChatAssistantChain initialized.")

    def get_memory_messages(self, query):
        try:
            history = self.memory.load_memory_variables(query).get("history", [])
            logger.debug(f"Loaded memory history:\n {history}\n\n")
            return history
        except Exception as e:
            logger.error(f"Error loading memory history: {e}")
            return []
    
    def _get_chain(self):
        try:
            # chain = (
            #     RunnablePassthrough.assign(history=RunnableLambda(self.get_memory_messages))|self.partial_prompt|self.llm|parser)
            agent = create_tool_calling_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=self.partial_prompt
            )
            
            partial_chain = AgentExecutor(
                agent=agent,
                tools=self.tools,
                memory=self.memory,
                # verbose=True
            )
            chain = partial_chain 
            logger.info("AgentExecutor chain initialized.")
            return chain
        except Exception as e:
            logger.error(f"Error initializing chain: {e}")
            raise
        
    async def run(self, user_input):
        try:
            # agent_executor = self.get_chain()
            response = await self.agent_executor.ainvoke({"input": user_input})
            return {"response": response["output"]}
        except Exception as e:
            logger.error(f"Error during chain execution: {e}")
            return None