from langchain_community.chat_models import ChatOpenAI
from langsmith import traceable
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from typing import TypedDict, Literal
from pymongo import MongoClient
import os

sessions_db = MongoClient(os.environ.get("MONGO_URI", "mongodb://localhost:27017/")).org_ai.sessions

llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

AgentType = Literal["crm-agent", "unknown"]

class ChatHistoryEntry(TypedDict):
    user: str
    assistant: str
    agent: AgentType

class AgentState(TypedDict, total=False):
    question: str
    chat_history: list[ChatHistoryEntry]
    session_id: str
    agent: AgentType
    answer: str

@traceable
def agent_node(question: str, chat_history: list[ChatHistoryEntry] | None = None) -> AgentState:
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