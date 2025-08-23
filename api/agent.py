from langchain_community.chat_models import ChatOpenAI
from langsmith import traceable
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, Literal, List, Optional, Dict, Any
from pymongo import MongoClient
from bson import ObjectId
from pydantic import BaseModel, Field, ConfigDict
import os
from functools import partial

from api.tools.web import search_web
from api.tools.google_sheet import read_google_sheet
from api.tools.google_drive import read_google_drive

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.sessions
agents_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.agents
connectors_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).nexa.connectors

Tools = Literal[
    "search_web",
]

Connectors = Literal[
    "google_sheet",
    "google_drive"
]

Models = Literal[
    "gpt-3.5-turbo",
    "gpt-4",
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "gpt-5"
]

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        from pydantic_core import core_schema
        def validate_object_id(v):
            if isinstance(v, ObjectId):
                return v
            if ObjectId.is_valid(v):
                return ObjectId(v)
            raise ValueError("Invalid ObjectId")

        return core_schema.json_or_python_schema(
            json_schema=core_schema.no_info_after_validator_function(
                validate_object_id, core_schema.str_schema()
            ),
            python_schema=core_schema.no_info_plain_validator_function(
                validate_object_id
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )

class Connector(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    connector_type: Connectors = Field(..., alias="connector_type")
    settings: Dict[str, Any]
    agent_id: PyObjectId = Field(..., alias="agent_id")

class ConnectorCreate(BaseModel):
    connector_type: Connectors
    settings: Dict[str, Any]

class ConnectorUpdate(BaseModel):
    settings: Optional[Dict[str, Any]] = None

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

class AgentCreate(BaseModel):
    name: str
    description: str
    model: Models
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    tools: List[Tools] = []

class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model: Optional[Models] = None
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    tools: Optional[List[Tools]] = None

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
async def get_agent_components(
    question: str,
    organization_id: ObjectId,
    chat_history: list | None = None,
    agent_id: str | None = None,
) -> tuple:
    question = question.strip()
    chat_history = chat_history or []
    selected_agent = None

    if agent_id:
        selected_agent = agents_db.find_one(
            {"_id": ObjectId(agent_id), "org": organization_id}
        )
    else:
        agents = list(agents_db.find({"org": organization_id}))
        if agents:
            agent_descriptions = "\n".join(
                [f"- **{agent['name']}**: {agent['description']}" for agent in agents]
            )
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
                HumanMessage(content=question),
            ]
            router_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            selected_agent_name_response = await router_llm.ainvoke(router_prompt)
            selected_agent_name = selected_agent_name_response.content.strip()
            selected_agent = next(
                (agent for agent in agents if agent["name"] == selected_agent_name),
                None,
            )

    if selected_agent:
        active_tools = [
            tool for tool in [
                search_web if "search_web" in selected_agent.get("tools", []) else None,
            ] if tool is not None
        ]

        agent_connectors = list(connectors_db.find({"agent_id": selected_agent["_id"]}))
        
        for connector in agent_connectors:
            match connector["connector_type"]:
                case "google_sheet":
                    configured_tool = partial(read_google_sheet, settings=connector["settings"])
                    
                    configured_tool.__doc__ = read_google_sheet.__doc__
                    
                    active_tools.append(configured_tool)
                case "google_drive":
                    configured_tool = partial(read_google_drive, settings=connector["settings"])
                    
                    configured_tool.__doc__ = read_google_drive.__doc__
                    
                    active_tools.append(configured_tool)
                
        
        agent_llm = ChatOpenAI(
            model=selected_agent["model"],
            temperature=selected_agent.get("temperature", 0.7),
            tools=active_tools,
            tool_choice="auto" if active_tools else None,
            streaming=True,
            max_retries=3
        )
        system_prompt = selected_agent["description"]
        final_agent_id = selected_agent["_id"]
        final_agent_name = selected_agent["name"]
    else:
        agent_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            max_retries=3
        )
        system_prompt = "You are a helpful general-purpose assistant."
        final_agent_id = None
        final_agent_name = "Generalist"

    messages = [SystemMessage(content=system_prompt)]
    for entry in chat_history:
        messages.append(HumanMessage(content=entry["user"]))
        messages.append(AIMessage(content=entry["assistant"]))
    messages.append(HumanMessage(content=question))

    return (
        agent_llm,
        messages,
        final_agent_name,
        str(final_agent_id) if final_agent_id else None,
    )