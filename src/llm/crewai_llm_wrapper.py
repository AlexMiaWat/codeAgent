"""
Обертка LLMManager для использования в CrewAI

Создает кастомный LLM для CrewAI, который использует LLMManager
для автоматического выбора моделей, fallback и параллельного выполнения.
"""

import logging
from typing import Optional, Any, Dict, List

from .llm_manager import LLMManager

logger = logging.getLogger(__name__)


class CrewAILLMWrapper:
    """
    Обертка LLMManager для CrewAI
    
    Использует LLMManager для:
    - Автоматического выбора самой быстрой модели
    - Fallback на резервные модели при ошибках
    - Параллельного выполнения через две модели с выбором лучшего ответа
    """
    
    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        config_path: str = "config/llm_settings.yaml",
        use_fastest: bool = True,
        use_parallel: bool = False
    ):
        """
        Инициализация обертки LLM для CrewAI
        
        Args:
            llm_manager: Экземпляр LLMManager (если None - создается новый)
            config_path: Путь к конфигурации LLM
            use_fastest: Использовать самую быструю модель
            use_parallel: Использовать параллельное выполнение (best_of_two)
        """
        if llm_manager is None:
            self.llm_manager = LLMManager(config_path)
        else:
            self.llm_manager = llm_manager
        
        self.use_fastest = use_fastest
        self.use_parallel = use_parallel
        
        logger.info(f"CrewAILLMWrapper initialized with {len(self.llm_manager.models)} models")
        logger.info(f"Use fastest: {use_fastest}, Use parallel: {use_parallel}")
    
    def call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """
        Синхронный вызов LLM (не используется CrewAI, но требуется для совместимости)
        
        Args:
            prompt: Текст запроса
            stop: Список стоп-слов
            run_manager: Менеджер выполнения
            **kwargs: Дополнительные параметры
        
        Returns:
            Ответ модели
        """
        # CrewAI использует async методы, но этот метод требуется для совместимости
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self.acall(prompt, stop=stop, run_manager=run_manager, **kwargs)
        )
    
    async def acall(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any
    ) -> str:
        """
        Асинхронный вызов LLM через LLMManager
        
        Args:
            prompt: Текст запроса
            stop: Список стоп-слов (игнорируется, так как LLMManager управляет этим)
            run_manager: Менеджер выполнения
            **kwargs: Дополнительные параметры
        
        Returns:
            Ответ модели
        """
        try:
            response = await self.llm_manager.generate_response(
                prompt=prompt,
                use_fastest=self.use_fastest,
                use_parallel=self.use_parallel
            )
            
            if response.success:
                return response.content
            else:
                error_msg = f"Model {response.model_name} failed: {response.error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
                
        except Exception as e:
            logger.error(f"Error in CrewAILLMWrapper.acall: {e}")
            raise
    
    def get_token_usage_summary(self) -> Dict[str, Any]:
        """Получить сводку использования токенов (для совместимости с CrewAI)"""
        return {
            "total_tokens": 0,
            "prompt_tokens": 0,
            "completion_tokens": 0
        }
    
    def completion_cost(self, total_tokens: int) -> float:
        """Вычислить стоимость завершения (для совместимости с CrewAI)"""
        return 0.0


def create_llm_for_crewai(
    config_path: str = "config/llm_settings.yaml",
    use_fastest: bool = True,
    use_parallel: bool = False
) -> CrewAILLMWrapper:
    """
    Фабричная функция для создания LLM для CrewAI
    
    Args:
        config_path: Путь к конфигурации LLM
        use_fastest: Использовать самую быструю модель
        use_parallel: Использовать параллельное выполнение
    
    Returns:
        CrewAILLMWrapper для использования в CrewAI
    """
    return CrewAILLMWrapper(
        llm_manager=None,
        config_path=config_path,
        use_fastest=use_fastest,
        use_parallel=use_parallel
    )
