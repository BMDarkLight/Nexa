from langchain_community.chat_models import ChatOpenAI
from langsmith import traceable
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, Literal
from pymongo import MongoClient
from bson import ObjectId
import os

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).org_ai.sessions
agents_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).org_ai.agents

Tools = Literal[""]
Models = Literal["gpt-3.5-turbo", "gpt-4", "gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-5"]

class Agent(TypedDict):
    _id: ObjectId
    name: str
    description: str
    org: ObjectId
    model: Models
    tools: list[Tools]
    created_at: str
    updated_at: str
    

class ChatHistoryEntry(TypedDict):
    user: str
    assistant: str
    agent: ObjectId | Literal["unknown"]

class AgentState(TypedDict, total=False):
    question: str
    chat_history: list[ChatHistoryEntry]
    session_id: str
    agent: ObjectId
    answer: str

@traceable
def agent_node(question: str, chat_history: list[ChatHistoryEntry] | None = None) -> AgentState:
    llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    question = question.strip()
    chat_history = chat_history or []

    summerizer = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

    summary_messages = [
        SystemMessage(content="You are a chat history summarizer. If there is no chat history, return nothing. Summarize this chat history:")
    ]

    for entry in chat_history:
        summary_messages.append(HumanMessage(content=entry['user']))
        summary_messages.append(AIMessage(content=entry['assistant']))

    summary = summerizer.invoke(summary_messages)

    if not chat_history:
        system_prompt = "You are a helpful assistant"
    else:
        system_prompt = f"You are a helpful assistant.\nHere is a summary of the chat history:\n{summary.content.strip()}\n"

    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ])

    raw_output = response.content.strip().lower()
    label = raw_output if raw_output in {"crm-agent"} else "unknown"

    return {
        "question": question,
        "chat_history": chat_history,
        "agent": label,
        "answer": response.content.strip()
    }