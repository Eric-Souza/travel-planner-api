from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

from app.services.llm.prompts.document import GROUNDED_ANSWER_PROMPT
from app.services.llm.provider import LLMProvider


def build_grounded_answer_chain(chat_model: ChatOllama):
    prompt = ChatPromptTemplate.from_template(GROUNDED_ANSWER_PROMPT)
    return prompt | chat_model | StrOutputParser()


async def invoke_grounded_answer(
    llm: LLMProvider,
    question: str,
    source_parts: list[str],
) -> str:
    sources = "\n\n".join(source_parts)
    from app.services.llm.langchain_provider import LangChainOllamaProvider

    if isinstance(llm, LangChainOllamaProvider):
        return await llm.grounded_answer(question, sources)

    prompt = GROUNDED_ANSWER_PROMPT.format(question=question, sources=sources)
    result = await llm.chat([{"role": "user", "content": prompt}])
    return result.content.strip()
