"""
Unit tests for LLMValidator
"""

import pytest
import json
from unittest.mock import MagicMock, AsyncMock, patch
from src.verification.llm_validator import LLMValidator
from src.quality.models.quality_result import VerificationLevel, QualityCheckType, QualityStatus


class TestLLMValidator:
    """Unit tests for LLMValidator"""

    def test_llm_validator_creation(self):
        """Test LLMValidator initialization"""
        validator = LLMValidator()

        assert validator.llm_manager is not None
        assert validator.code_quality_threshold == 0.7
        assert validator.task_compliance_threshold == 0.8
        assert validator.logic_validation_threshold == 0.75

    def test_llm_validator_with_custom_llm_manager(self):
        """Test LLMValidator with custom LLM manager"""
        mock_llm_manager = MagicMock()
        validator = LLMValidator(llm_manager=mock_llm_manager)

        assert validator.llm_manager == mock_llm_manager

    def test_llm_validator_with_config(self):
        """Test LLMValidator with custom config"""
        config = {
            'code_quality_threshold': 0.8,
            'task_compliance_threshold': 0.9,
            'logic_validation_threshold': 0.85
        }

        validator = LLMValidator(config=config)

        assert validator.code_quality_threshold == 0.8
        assert validator.task_compliance_threshold == 0.9
        assert validator.logic_validation_threshold == 0.85

    @pytest.mark.asyncio
    async def test_validate_code_quality_success(self):
        """Test successful code quality validation"""
        validator = LLMValidator()

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            'overall_score': 0.85,
            'readability_score': 0.9,
            'maintainability_score': 0.8,
            'issues': [
                {
                    'type': 'warning',
                    'description': 'Missing docstring',
                    'severity': 'low',
                    'file': 'test.py'
                }
            ],
            'strengths': ['Good naming conventions'],
            'recommendations': ['Add type hints']
        })
        mock_response.model_name = 'test-model'

        validator.llm_manager.generate_response = AsyncMock(return_value=mock_response)

        code_changes = {
            'task_id': 'test_task',
            'files_changed': ['test.py'],
            'lines_added': 50,
            'code_snippets': [{'file': 'test.py', 'content': 'def test():\n    pass'}]
        }

        result = await validator.validate_code_quality(code_changes)

        assert result.task_id == 'test_task'
        assert result.verification_level == VerificationLevel.AI_VALIDATION
        assert result.execution_time >= 0
        assert result.quality_result.results[0].score == 0.85
        assert result.metadata['analysis_type'] == 'code_quality'
        assert result.metadata['llm_model'] == 'test-model'

    @pytest.mark.asyncio
    async def test_validate_code_quality_llm_failure(self):
        """Test code quality validation with LLM failure"""
        validator = LLMValidator()

        # Mock failed LLM response
        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error = 'LLM service unavailable'

        validator.llm_manager.generate_response = AsyncMock(return_value=mock_response)

        code_changes = {'task_id': 'test_task'}

        result = await validator.validate_code_quality(code_changes)

        assert result.task_id == 'test_task'
        assert result.verification_level == VerificationLevel.AI_VALIDATION
        assert result.quality_result.results[0].status == QualityStatus.ERROR
        assert 'LLM analysis failed' in result.quality_result.results[0].message

    @pytest.mark.asyncio
    async def test_validate_task_compliance_success(self):
        """Test successful task compliance validation"""
        validator = LLMValidator()

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            'compliance_score': 0.9,
            'requirements_met': ['Function implemented', 'Tests added'],
            'requirements_missing': [],
            'issues': [],
            'overall_assessment': 'Task completed successfully'
        })
        mock_response.model_name = 'compliance-model'

        validator.llm_manager.generate_response = AsyncMock(return_value=mock_response)

        task_description = "Implement user authentication function with tests"
        execution_result = {
            'status': 'completed',
            'functions_implemented': ['authenticate_user'],
            'tests_added': 5
        }

        result = await validator.validate_task_compliance(task_description, execution_result)

        assert result.task_id == 'unknown'  # No task_id in execution_result
        assert result.verification_level == VerificationLevel.AI_VALIDATION
        assert result.quality_result.results[0].score == 0.9
        assert result.metadata['analysis_type'] == 'task_compliance'

    @pytest.mark.asyncio
    async def test_validate_logic_correctness_success(self):
        """Test successful logic validation"""
        validator = LLMValidator()

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            'logic_score': 0.75,
            'logic_issues': [
                {
                    'type': 'edge_case',
                    'description': 'Missing null check',
                    'severity': 'medium',
                    'file': 'logic.py'
                }
            ],
            'logic_strengths': ['Good algorithm structure'],
            'edge_cases': ['Handle empty input'],
            'logic_flow_assessment': 'Logic is sound but needs edge case handling'
        })
        mock_response.model_name = 'logic-model'

        validator.llm_manager.generate_response = AsyncMock(return_value=mock_response)

        code_changes = {
            'task_id': 'logic_task',
            'code_changes': [{'file': 'logic.py', 'change': 'Added validation logic'}],
            'existing_code': [{'file': 'logic.py', 'content': 'def validate(data):\n    return len(data) > 0'}]
        }

        result = await validator.validate_logic_correctness(code_changes)

        assert result.task_id == 'logic_task'
        assert result.verification_level == VerificationLevel.AI_VALIDATION
        assert result.quality_result.results[0].score == 0.75
        assert result.metadata['analysis_type'] == 'logic_validation'

    @pytest.mark.asyncio
    async def test_ai_validation_no_analysis_data(self):
        """Test AI validation with no analysis data"""
        validator = LLMValidator()

        # Test with empty analysis data
        result = await validator.validate_code_quality({})

        assert result.quality_result.results[0].status == QualityStatus.SKIPPED
        assert 'No analysis data provided' in result.quality_result.results[0].message

    @pytest.mark.asyncio
    async def test_parallel_ai_validations(self):
        """Test parallel execution of multiple AI validations"""
        validator = LLMValidator()

        # Mock multiple LLM responses
        mock_response1 = MagicMock()
        mock_response1.success = True
        mock_response1.content = json.dumps({'overall_score': 0.8})

        mock_response2 = MagicMock()
        mock_response2.success = True
        mock_response2.content = json.dumps({'logic_score': 0.7})

        # Mock the validator methods
        validator.llm_manager.generate_response = AsyncMock()
        validator.llm_manager.generate_response.side_effect = [mock_response1, mock_response2]

        # Mock the individual validation methods
        validator.validate_code_quality = AsyncMock(return_value=MagicMock(overall_score=0.8, quality_result=MagicMock(results=[])))
        validator.validate_logic_correctness = AsyncMock(return_value=MagicMock(overall_score=0.7, quality_result=MagicMock(results=[])))

        code_changes = {
            'code_changes': [{'file': 'test.py'}],
            'task_description': 'Test task'
        }

        result = await validator.validate_logic_correctness(code_changes)

        # Should have called LLM manager for analysis
        assert validator.llm_manager.generate_response.called

    @pytest.mark.asyncio
    async def test_generate_improvement_suggestions_success(self):
        """Test successful generation of improvement suggestions"""
        validator = LLMValidator()

        mock_response = MagicMock()
        mock_response.success = True
        mock_response.content = json.dumps({
            'suggestions': [
                {
                    'category': 'performance',
                    'priority': 'high',
                    'description': 'Optimize database queries',
                    'implementation_effort': 'medium',
                    'expected_benefit': 'Reduce response time by 50%'
                }
            ]
        })

        validator.llm_manager.generate_response = AsyncMock(return_value=mock_response)

        analysis_data = {'issues': ['Slow queries'], 'context': 'web_app'}

        suggestions = await validator.generate_improvement_suggestions(analysis_data)

        assert isinstance(suggestions, list)
        assert len(suggestions) == 1
        assert suggestions[0]['category'] == 'performance'
        assert suggestions[0]['priority'] == 'high'

    @pytest.mark.asyncio
    async def test_generate_improvement_suggestions_failure(self):
        """Test improvement suggestions generation failure"""
        validator = LLMValidator()

        mock_response = MagicMock()
        mock_response.success = False
        mock_response.error = 'LLM failed'

        validator.llm_manager.generate_response = AsyncMock(return_value=mock_response)

        suggestions = await validator.generate_improvement_suggestions({})

        assert suggestions == []

    def test_prepare_code_analysis_data(self):
        """Test preparation of code analysis data"""
        validator = LLMValidator()

        code_changes = {
            'files_changed': ['src/main.py', 'test/test.py'],
            'lines_added': 100,
            'lines_removed': 20,
            'code_snippets': [
                {'file': 'src/main.py', 'content': 'def hello():\n    print("Hello")'},
                {'file': 'test/test.py', 'content': 'def test_hello():\n    assert True'}
            ],
            'language': 'python',
            'extra_field': 'should_be_ignored'
        }

        context = {'project_type': 'web_app'}

        analysis_data = validator._prepare_code_analysis_data(code_changes, context)

        assert analysis_data['files_changed'] == ['src/main.py', 'test/test.py']
        assert analysis_data['lines_added'] == 100
        assert analysis_data['lines_removed'] == 20
        assert len(analysis_data['code_snippets']) == 2
        assert analysis_data['language'] == 'python'
        assert analysis_data['project_context'] == context
        assert 'extra_field' not in analysis_data

    def test_prepare_logic_analysis_data(self):
        """Test preparation of logic analysis data"""
        validator = LLMValidator()

        code_changes = {
            'code_changes': [{'file': 'logic.py', 'change': 'Added validation'}],
            'task_description': 'Implement validation',
            'existing_code': [{'file': 'logic.py', 'content': 'def validate(): pass'}],
            'dependencies': ['requests'],
            'extra_data': 'ignored'
        }

        context = {'complexity': 'medium'}

        analysis_data = validator._prepare_logic_analysis_data(code_changes, context)

        assert analysis_data['code_changes'] == [{'file': 'logic.py', 'change': 'Added validation'}]
        assert analysis_data['task_description'] == 'Implement validation'
        assert len(analysis_data['existing_code']) == 1
        assert analysis_data['dependencies'] == ['requests']
        assert analysis_data['context'] == context

    def test_create_code_quality_prompt(self):
        """Test creation of code quality analysis prompt"""
        validator = LLMValidator()

        analysis_data = {
            'files_changed': 2,
            'lines_added': 150,
            'lines_removed': 30,
            'language': 'python',
            'code_snippets': [
                {'file': 'utils.py', 'content': 'def helper():\n    return True'},
                {'file': 'main.py', 'content': 'if __name__ == "__main__":\n    main()'}
            ]
        }

        prompt = validator._create_code_quality_prompt(analysis_data)

        assert 'Analyze the code quality' in prompt
        assert 'Files changed: 2' in prompt
        assert 'Lines added: 150' in prompt
        assert 'Lines removed: 30' in prompt
        assert 'Language: python' in prompt
        assert 'File: utils.py' in prompt
        assert 'File: main.py' in prompt
        assert 'readability and style' in prompt

    def test_create_task_compliance_prompt(self):
        """Test creation of task compliance analysis prompt"""
        validator = LLMValidator()

        analysis_data = {
            'task_description': 'Create user registration API',
            'execution_result': {
                'endpoints_created': ['POST /api/register'],
                'status': 'completed'
            },
            'context': {'framework': 'FastAPI'}
        }

        prompt = validator._create_task_compliance_prompt(analysis_data)

        assert 'whether the execution result properly fulfills the task requirements' in prompt
        assert 'Create user registration API' in prompt
        assert 'POST /api/register' in prompt
        assert 'FastAPI' in prompt

    def test_create_logic_validation_prompt(self):
        """Test creation of logic validation prompt"""
        validator = LLMValidator()

        analysis_data = {
            'task_description': 'Implement sorting algorithm',
            'code_changes': [
                {'file': 'sort.py', 'change': 'Added quicksort implementation'},
                {'file': 'sort.py', 'change': 'Added merge sort as fallback'}
            ],
            'existing_code': [
                {'file': 'sort.py', 'content': 'def quicksort(arr):\n    # Implementation'}
            ]
        }

        prompt = validator._create_logic_validation_prompt(analysis_data)

        assert 'Analyze the logical correctness' in prompt
        assert 'Implement sorting algorithm' in prompt
        assert 'Added quicksort implementation' in prompt
        assert 'Added merge sort as fallback' in prompt
        assert 'logical correctness of algorithms' in prompt

    def test_create_improvement_suggestions_prompt(self):
        """Test creation of improvement suggestions prompt"""
        validator = LLMValidator()

        analysis_data = {
            'issues': ['Slow performance', 'High memory usage'],
            'context': 'data_processing_app'
        }

        prompt = validator._create_improvement_suggestions_prompt(analysis_data)

        assert 'generate specific improvement suggestions' in prompt
        assert 'Slow performance' in prompt
        assert 'High memory usage' in prompt
        assert 'data_processing_app' in prompt

    def test_parse_code_quality_analysis_valid_json(self):
        """Test parsing valid code quality analysis JSON"""
        validator = LLMValidator()

        content = json.dumps({
            'overall_score': 0.85,
            'issues': [{'type': 'warning', 'description': 'Test issue'}],
            'strengths': ['Good structure'],
            'recommendations': ['Add tests']
        })

        result = validator._parse_code_quality_analysis(content)

        assert result['overall_score'] == 0.85
        assert len(result['issues']) == 1
        assert result['strengths'] == ['Good structure']
        assert result['recommendations'] == ['Add tests']

    def test_parse_code_quality_analysis_invalid_json(self):
        """Test parsing invalid code quality analysis JSON"""
        validator = LLMValidator()

        content = 'invalid json content'

        result = validator._parse_code_quality_analysis(content)

        assert result['overall_score'] == 0.5
        assert len(result['issues']) == 1
        assert 'Failed to parse' in result['issues'][0]['description']

    def test_parse_task_compliance_analysis_valid_json(self):
        """Test parsing valid task compliance analysis JSON"""
        validator = LLMValidator()

        content = json.dumps({
            'compliance_score': 0.9,
            'requirements_met': ['API created'],
            'requirements_missing': ['Tests missing'],
            'issues': [{'type': 'missing_tests'}],
            'overall_assessment': 'Good job'
        })

        result = validator._parse_task_compliance_analysis(content)

        assert result['compliance_score'] == 0.9
        assert result['requirements_met'] == ['API created']
        assert result['requirements_missing'] == ['Tests missing']

    def test_parse_task_compliance_analysis_invalid_json(self):
        """Test parsing invalid task compliance analysis JSON"""
        validator = LLMValidator()

        content = 'not json'

        result = validator._parse_task_compliance_analysis(content)

        assert result['compliance_score'] == 0.5
        assert len(result['issues']) == 1
        assert 'Failed to parse' in result['issues'][0]['description']

    def test_parse_logic_validation_analysis_valid_json(self):
        """Test parsing valid logic validation analysis JSON"""
        validator = LLMValidator()

        content = json.dumps({
            'logic_score': 0.8,
            'logic_issues': [{'type': 'edge_case', 'description': 'Null handling'}],
            'logic_strengths': ['Clean logic'],
            'edge_cases': ['Empty input'],
            'logic_flow_assessment': 'Good flow'
        })

        result = validator._parse_logic_validation_analysis(content)

        assert result['logic_score'] == 0.8
        assert len(result['logic_issues']) == 1
        assert result['logic_strengths'] == ['Clean logic']

    def test_parse_logic_validation_analysis_invalid_json(self):
        """Test parsing invalid logic validation analysis JSON"""
        validator = LLMValidator()

        content = 'invalid'

        result = validator._parse_logic_validation_analysis(content)

        assert result['logic_score'] == 0.5
        assert len(result['logic_issues']) == 1

    def test_create_quality_result_from_analysis(self):
        """Test creation of quality result from analysis"""
        validator = LLMValidator()

        analysis_result = {
            'overall_score': 0.75,
            'issues': [
                {'severity': 'high', 'description': 'Critical bug'},
                {'severity': 'low', 'description': 'Minor issue'}
            ]
        }

        quality_result = validator._create_quality_result_from_analysis(
            analysis_result, QualityCheckType.CODE_QUALITY_AI
        )

        assert quality_result.check_type == QualityCheckType.CODE_QUALITY_AI
        assert quality_result.score == 0.75
        assert quality_result.status == QualityStatus.WARNING  # Has high severity issue
        assert '0.75' in quality_result.message

    def test_create_error_result(self):
        """Test creation of error result"""
        from datetime import datetime
        validator = LLMValidator()

        start_time = datetime.now()
        error_result = validator._create_error_result(
            "code_quality", "Test error", start_time
        )

        assert error_result.verification_level == VerificationLevel.AI_VALIDATION
        assert error_result.quality_result.results[0].status == QualityStatus.ERROR
        assert 'Test error' in error_result.quality_result.results[0].message
        assert error_result.execution_time >= 0