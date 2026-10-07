from langchain_core.messages import HumanMessage, SystemMessage

from data_analyst.agent.llm import invoke_structured
from data_analyst.agent.model_provider import create_chat_model
from data_analyst.agent.models import QuestionIntent
from data_analyst.config import Settings


def main() -> None:
    settings = Settings()
    model = create_chat_model(settings)

    print(f"Modelo: {settings.gemini_model}")
    print(
        f"Limite local: {settings.gemini_requests_per_minute} "
        "requisições/minuto"
    )
    print("Aguardando o limitador local antes da chamada de teste...")

    result = invoke_structured(
        model,
        QuestionIntent,
        [
            SystemMessage(
                content=(
                    "Interprete a pergunta de negócio. "
                    "Não gere SQL e seja objetivo."
                )
            ),
            HumanMessage(
                content="Quantos clientes compraram via App?"
            ),
        ],
    )

    print("OK: structured output recebido")
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
