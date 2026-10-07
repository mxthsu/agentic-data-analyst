from data_analyst.service import _aggregate_token_usage


def test_agrega_tokens_de_todas_as_chamadas_do_modelo() -> None:
    usage = _aggregate_token_usage(
        {
            "gemini-a": {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
            "gemini-b": {
                "input_tokens": 50,
                "output_tokens": 10,
                "total_tokens": 60,
            },
        }
    )

    assert usage.input_tokens == 150
    assert usage.output_tokens == 30
    assert usage.total_tokens == 180


def test_calcula_total_quando_provider_nao_informa_total() -> None:
    usage = _aggregate_token_usage(
        {
            "gemini": {
                "input_tokens": 80,
                "output_tokens": 25,
            }
        }
    )

    assert usage.input_tokens == 80
    assert usage.output_tokens == 25
    assert usage.total_tokens == 105
