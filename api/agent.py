from langchain_community.chat_models import ChatOpenAI
from langsmith import traceable
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, Literal
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
import os

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).org_ai.sessions
agents_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).org_ai.agents

Tools = Literal[""]
Models = Literal[
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo"
]

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        return core_schema.no_info_after_validator_function(
            cls.validate,
            core_schema.str_schema()
        )

    @classmethod
    def validate(cls, value):
        if not ObjectId.is_valid(value):
            raise ValueError("Invalid ObjectId")
        return ObjectId(value)

class Agent(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    name: str
    description: str
    org: PyObjectId
    model: Models
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    tools: list[Tools]
    created_at: str
    updated_at: str
    

class ChatHistoryEntry(TypedDict):
    user: str
    assistant: str
    agent_id: str | None
    agent_name: str

class AgentState(TypedDict, total=False):
    question: str
    chat_history: list[ChatHistoryEntry]
    agent_id: str | None
    agent_name: str
    answer: str

@traceable
def agent_node(question: str, organization_id: ObjectId, chat_history: list[ChatHistoryEntry] | None = None, agent_id: str | None = None) -> AgentState:
    question = question.strip()
    chat_history = chat_history or []
    
    selected_agent = None

    if agent_id:
        selected_agent = agents_db.find_one({
            "_id": ObjectId(agent_id),
            "org": organization_id
        })
    else:
        agents = list(agents_db.find({"org": organization_id}))
        if agents:
            agent_descriptions = "\n".join([f"- **{agent['name']}**: {agent['description']}" for agent in agents])
            
            router_prompt = [
                SystemMessage(
                    content=(
                        "You are an expert at routing a user's request to the correct agent. "
                        "Based on the user's question, select the best agent from the following list. "
                        "You must output **only the name** of the agent you choose. "
                        "If no agent seems suitable for the request, you must output 'Generalist'."
                        f"\n\nAvailable Agents:\n{agent_descriptions}"
                    )
                ),
                HumanMessage(content=question)
            ]
            
            router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            selected_agent_name = router_llm.invoke(router_prompt).content.strip()
            
            selected_agent = next((agent for agent in agents if agent['name'] == selected_agent_name), None)

    if selected_agent:
        agent_llm = ChatOpenAI(model=selected_agent["model"], temperature=selected_agent.get("temperature", 0.7))
        system_prompt = selected_agent["description"]
        final_agent_id = selected_agent["_id"]
        final_agent_name = selected_agent["name"]
    else:
        agent_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.7)
        system_prompt = "You are a helpful general-purpose assistant."
        final_agent_id = None
        final_agent_name = "Generalist"
        
    messages = [SystemMessage(content=system_prompt)]
    for entry in chat_history:
        messages.append(HumanMessage(content=entry['user']))
        messages.append(AIMessage(content=entry['assistant']))
    messages.append(HumanMessage(content=question))
    
    response = agent_llm.invoke(messages)
    answer = response.content.strip()

    return {
        "question": question,
        "chat_history": chat_history,
        "agent_id": str(final_agent_id) if final_agent_id else None,
        "agent_name": final_agent_name,
        "answer": answer
    }