# Диаграмма архитектуры нового LLM модуля

## Обзор архитектуры

Новая модульная архитектура LLM Manager разделена на специализированные компоненты с четким разделением ответственностей.

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLMManager (Фасад)                        │
│                                                                 │
│  Единый интерфейс для всех операций с LLM                       │
│  Управление жизненным циклом компонентов                        │
│  Dependency Injection                                           │
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  │ depends on
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Component Dependencies                       │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │             │    │             │    │             │         │
│  │ ModelRegistry│◄───┤StrategyMgr  │◄───┤ResponseEval │         │
│  │             │    │             │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│           ▲                    ▲                    ▲           │
│           │                    │                    │           │
│           │                    │                    │           │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │             │    │             │    │             │         │
│  │ ClientManager│    │JsonValidator│    │HealthMonitor│         │
│  │             │    │             │    │             │         │
│  └─────────────┘    └─────────────┘    └─────────────┘         │
│                                                                 │
│  ┌─────────────┐                                               │
│  │             │                                               │
│  │ConfigLoader │                                               │
│  │             │                                               │
│  └─────────────┘                                               │
└─────────────────────────────────────────────────────────────────┘
```

## Детальная диаграмма зависимостей

### LLMManager (Фасад)
```
LLMManager
├── generate_response()     -> StrategyManager.generate()
├── get_primary_models()    -> ModelRegistry.get_models_by_role()
├── evaluate_response()     -> ResponseEvaluator.evaluate_response()
├── validate_json()         -> JsonValidator.validate_json()
├── check_health()          -> HealthMonitor.check_health()
└── get_stats()             -> Aggregation of all components
```

### ModelRegistry
```
ModelRegistry
├── ConfigLoader (dependency injection)
├── _load_config()
├── _init_models()
├── get_models_by_role()
├── get_model()
├── update_model_stats()
└── get_fastest_model()
```

### ClientManager
```
ClientManager
├── ConfigLoader (dependency injection)
├── _load_config()
├── _init_clients()
├── _get_provider_for_model()
├── _get_client_for_model()
└── call_model() -> AsyncOpenAI
```

### StrategyManager
```
StrategyManager
├── ModelRegistry (inject)
├── ClientManager (inject)
├── ResponseEvaluator (inject)
├── JsonValidator (inject)
├── generate() -> _generate_single() | _generate_parallel()
├── _generate_single()
├── _generate_with_fallback()
├── _generate_parallel()
└── _select_best_response()
```

### ResponseEvaluator
```
ResponseEvaluator
├── ClientManager (inject)
├── evaluate_response()
├── compare_responses()
├── select_best_response()
├── _create_evaluation_prompt()
└── _parse_evaluation_response()
```

### JsonValidator
```
JsonValidator
├── __init__()
├── validate_json()
├── extract_json_from_text()
├── validate_and_extract()
└── fix_malformed_json()
```

### HealthMonitor
```
HealthMonitor
├── ModelRegistry (inject)
├── ClientManager (inject)
├── start_monitoring()
├── stop_monitoring()
├── check_health()
├── _perform_health_checks()
├── _check_single_model()
├── disable_model()
├── enable_model()
├── _handle_unhealthy_model()
└── _try_recover_models()
```

### ConfigLoader
```
ConfigLoader
├── load_config()
├── substitute_env_vars()
├── validate_config()
└── _substitute_single_env_var()
```

## Поток данных при генерации ответа

### Single Model Generation
```
User Request
    ↓
LLMManager.generate_response()
    ↓
StrategyManager._generate_single()
    ↓
ModelRegistry.get_fastest_model()
    ↓
ClientManager.call_model()
    ↓
AsyncOpenAI API call
    ↓
ModelResponse (success/failure)
    ↑
JsonValidator.validate_json() [if JSON mode]
    ↑
ModelRegistry.update_model_stats()
    ↑
Return to user
```

### Parallel Generation (Best of Two)
```
User Request
    ↓
LLMManager.generate_response(use_parallel=True)
    ↓
StrategyManager._generate_parallel()
    ↓
asyncio.gather([
    ClientManager.call_model(model1),
    ClientManager.call_model(model2)
])
    ↓
[ModelResponse1, ModelResponse2]
    ↓
JsonValidator.validate_and_extract() [for each]
    ↓
ResponseEvaluator.compare_responses()
    ↓
Select best by score
    ↓
ModelRegistry.update_model_stats()
    ↑
Return best response
```

## Health Monitoring Flow
```
HealthMonitor (background task)
    ↓
_perform_health_checks() every 5 min
    ↓
For each model:
    _check_single_model()
        ↓
    ClientManager.call_model(test_prompt)
        ↓
    Evaluate response quality
        ↓
    Update model status
        ↓
    _handle_unhealthy_model() if failed
        ↓
    Disable model after 3 failures
    Later: _try_recover_models()
```

## Configuration Flow
```
Config file (YAML)
    ↓
ConfigLoader.load_config()
    ↓
Substitute ${ENV_VARS}
    ↓
Validate structure
    ↓
ModelRegistry._load_config()
    ↓
ModelRegistry._init_models()
    ↓
ClientManager._load_config()
    ↓
ClientManager._init_clients()
    ↓
All components ready
```

## Error Handling Strategy

### Fallback Chain
```
Primary Model → Reserve Models → Fallback Models → Last Response → Default Error Response
     ↓             ↓                ↓                ↓                ↓
   Success?      Success?        Success?        Return           Return
      ↓             ↓                ↓             last resp       error msg
   Return        Return           Return
  response      response         response
```

### JSON Mode Special Handling
```
JSON Request
    ↓
Use parallel generation by default
    ↓
Validate each response with JsonValidator
    ↓
Skip models with previous JSON failures
    ↓
Prioritize models with good JSON history
    ↓
Extract JSON from malformed responses
    ↓
Return validated JSON or fallback
```

## Component Lifecycle

### Initialization Order
1. ConfigLoader (standalone)
2. ModelRegistry (depends on ConfigLoader)
3. ClientManager (depends on ConfigLoader)
4. JsonValidator (standalone)
5. ResponseEvaluator (depends on ClientManager)
6. StrategyManager (depends on Registry, Client, Evaluator, Validator)
7. HealthMonitor (depends on Registry, Client)
8. LLMManager (facade, injects all components)

### Shutdown Order
1. HealthMonitor.stop_monitoring()
2. LLMManager (cleanup references)
3. Other components (garbage collected)

## Benefits of New Architecture

### Maintainability
- **Single Responsibility**: Each component has one clear purpose
- **Dependency Injection**: Loose coupling between components
- **Interface Segregation**: Clear contracts between components

### Testability
- **Isolation**: Each component can be tested independently
- **Mocking**: Easy to mock dependencies for unit tests
- **Focused Tests**: Tests target specific functionality

### Extensibility
- **New Strategies**: Easy to add new generation strategies
- **New Providers**: Simple to add new LLM providers
- **New Evaluators**: Pluggable response evaluation logic

### Reliability
- **Health Monitoring**: Automatic detection and recovery
- **Fallback Chains**: Multiple levels of error recovery
- **Graceful Degradation**: System continues working even with failures

### Performance
- **Parallel Processing**: Concurrent model calls where beneficial
- **Smart Selection**: Automatic choice of fastest available models
- **Connection Pooling**: Efficient use of API connections