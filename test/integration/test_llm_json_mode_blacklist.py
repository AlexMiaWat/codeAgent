import pytest

from src.llm.llm_manager import LLMManager, ModelConfig, ModelRole, ModelResponse


@pytest.mark.anyio
async def test_json_mode_invalid_json_triggers_fallback_and_blacklist(monkeypatch):
    """
    Репродукция кейса из лога:
    - первая модель в JSON mode возвращает обычный текст (не JSON)
    - менеджер должен перейти к следующей модели
    - модель-нарушитель должна попадать в blacklist, чтобы второй JSON-запрос ее не дергал
    """

    # Не трогаем реальные ключи/сеть
    monkeypatch.setattr(LLMManager, "_init_clients", lambda self: None)

    mgr = LLMManager("config/llm_settings.yaml")

    # Переопределяем набор моделей на минимальный детерминированный
    bad = ModelConfig(
        name="meta-llama/llama-3.2-1b-instruct",
        max_tokens=128,
        context_window=4096,
        role=ModelRole.PRIMARY,
        enabled=True,
    )
    good = ModelConfig(
        name="good-json-model",
        max_tokens=128,
        context_window=4096,
        role=ModelRole.FALLBACK,
        enabled=True,
    )
    mgr.models = {bad.name: bad, good.name: good}

    calls: list[str] = []

    async def fake_call_model(prompt: str, model_config: ModelConfig, response_format=None) -> ModelResponse:
        calls.append(model_config.name)

        # Воспроизводим предупреждение из лога: текст вместо JSON
        if model_config.name == bad.name:
            return ModelResponse(
                model_name=model_config.name,
                content="Пусть `usefulness_percent` — это процентное значение, которое отражает полезность задачи...",
                response_time=0.01,
                success=True,
            )

        # Валидный JSON-объект
        return ModelResponse(
            model_name=model_config.name,
            content='{"usefulness_percent": 55, "comment": "ok"}',
            response_time=0.01,
            success=True,
        )

    monkeypatch.setattr(mgr, "_call_model", fake_call_model)

    json_response_format = {"type": "json_object"}
    prompt = 'Верни JSON: {"usefulness_percent": 0, "comment": "x"}'

    # 1) Первый запрос: плохая модель -> invalid JSON -> fallback на хорошую
    resp1 = await mgr.generate_response(prompt=prompt, use_fastest=True, use_parallel=False, response_format=json_response_format)
    assert resp1.success is True
    assert resp1.model_name == good.name
    assert bad.name in mgr._json_mode_blacklist
    assert calls == [bad.name, good.name]

    # 2) Второй запрос: blacklist должен исключить bad модель (сразу good)
    calls.clear()
    resp2 = await mgr.generate_response(prompt=prompt, use_fastest=True, use_parallel=False, response_format=json_response_format)
    assert resp2.success is True
    assert resp2.model_name == good.name
    assert calls == [good.name]

