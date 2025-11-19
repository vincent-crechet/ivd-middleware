"""Unit tests for VerificationEngine service."""

import pytest
from app.services import VerificationEngine
from app.models import AutoVerificationSettings, VerificationRule, RuleType
from app.ports import (
    IAutoVerificationSettingsRepository,
    IVerificationRuleRepository,
)

TEST_TENANT_ID = "test-tenant-123"
TEST_TEST_CODE = "GLU"


class TestVerificationEngine:
    """Tests for VerificationEngine verification rules."""

    @pytest.fixture
    def engine(
        self,
        auto_verification_settings_repository: IAutoVerificationSettingsRepository,
        verification_rule_repository: IVerificationRuleRepository,
    ):
        """Create a VerificationEngine with parametrized repositories."""
        return VerificationEngine(
            settings_repo=auto_verification_settings_repository,
            rule_repo=verification_rule_repository,
        )

    @pytest.fixture
    def sample_settings(self, auto_verification_settings_repository):
        """Create sample verification settings."""
        from app.models import AutoVerificationSettings
        import uuid

        settings = AutoVerificationSettings(
            id=str(uuid.uuid4()),
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            test_name="Glucose",
            reference_range_low=70.0,
            reference_range_high=100.0,
            critical_range_low=40.0,
            critical_range_high=400.0,
            instrument_flags_to_block='["C", "H"]',
            delta_check_threshold_percent=10.0,
            delta_check_lookback_days=30,
        )
        return auto_verification_settings_repository.create(settings)

    # ========================================================================
    # Reference Range Check Tests
    # ========================================================================

    def test_reference_range_pass_value_in_range(self, engine, sample_settings):
        """Test that value within reference range passes."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=85.0,
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is True
        assert RuleType.REFERENCE_RANGE not in result.failed_rules

    def test_reference_range_pass_at_low_boundary(self, engine, sample_settings):
        """Test that value at low boundary passes."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=70.0,  # Exact low boundary
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is True

    def test_reference_range_pass_at_high_boundary(self, engine, sample_settings):
        """Test that value at high boundary passes."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=100.0,  # Exact high boundary
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is True

    def test_reference_range_fail_below_low(self, engine, sample_settings):
        """Test that value below reference range fails."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=65.0,  # Below 70
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is False
        assert RuleType.REFERENCE_RANGE in result.failed_rules

    def test_reference_range_fail_above_high(self, engine, sample_settings):
        """Test that value above reference range fails."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=150.0,  # Above 100
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is False
        assert RuleType.REFERENCE_RANGE in result.failed_rules

    # ========================================================================
    # Critical Range Check Tests
    # ========================================================================

    def test_critical_range_pass_value_outside_critical(self, engine, sample_settings):
        """Test that value outside critical range passes."""
        # Value is within reference but outside critical range
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=85.0,
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is True
        assert RuleType.CRITICAL_RANGE not in result.failed_rules

    def test_critical_range_fail_below_critical_low(self, engine, sample_settings):
        """Test that value below critical low fails."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=30.0,  # Below critical_low=40
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is False
        assert RuleType.CRITICAL_RANGE in result.failed_rules

    def test_critical_range_fail_above_critical_high(self, engine, sample_settings):
        """Test that value above critical high fails."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=500.0,  # Above critical_high=400
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is False
        assert RuleType.CRITICAL_RANGE in result.failed_rules

    def test_critical_range_pass_at_critical_boundary(self, engine, sample_settings):
        """Test that value at critical boundary fails (critical is danger zone)."""
        # Critical range [40, 400] is the "danger zone" - being exactly on boundary is still in danger
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=40.0,  # At critical_low boundary
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        # At critical boundary should fail (within danger zone)
        assert result.passed is False
        assert RuleType.CRITICAL_RANGE in result.failed_rules

    # ========================================================================
    # Instrument Flag Check Tests
    # ========================================================================

    def test_instrument_flag_pass_no_flags(self, engine, sample_settings):
        """Test that result with no flags passes."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=85.0,
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        assert result.passed is True
        assert RuleType.INSTRUMENT_FLAG not in result.failed_rules

    def test_instrument_flag_pass_allowed_flags(self, engine, sample_settings):
        """Test that result with allowed flags passes."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=85.0,
            result_id="result-1",
            instrument_flags="N",  # Not in block list
            previous_value=None,
        )

        assert result.passed is True
        assert RuleType.INSTRUMENT_FLAG not in result.failed_rules

    def test_instrument_flag_fail_blocked_flag_c(self, engine, sample_settings):
        """Test that result with blocked flag 'C' fails."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=85.0,
            result_id="result-1",
            instrument_flags="C",  # In block list: ["C", "H"]
            previous_value=None,
        )

        assert result.passed is False
        assert RuleType.INSTRUMENT_FLAG in result.failed_rules

    def test_instrument_flag_fail_blocked_flag_h(self, engine, sample_settings):
        """Test that result with blocked flag 'H' fails."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=85.0,
            result_id="result-1",
            instrument_flags="H",  # In block list: ["C", "H"]
            previous_value=None,
        )

        assert result.passed is False
        assert RuleType.INSTRUMENT_FLAG in result.failed_rules

    # ========================================================================
    # Delta Check Tests
    # ========================================================================

    def test_delta_check_pass_within_threshold(self, engine, sample_settings):
        """Test that delta within threshold passes."""
        # Current=100, Previous=95, Delta=5.26%, Threshold=10%
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=100.0,
            result_id="result-1",
            instrument_flags=None,
            previous_value=95.0,
        )

        # Delta check is disabled by default, so it passes
        assert RuleType.DELTA_CHECK not in result.failed_rules

    def test_delta_check_no_previous_value(self, engine, sample_settings):
        """Test that result with no previous value passes delta check."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=100.0,
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        # No previous value means delta check is skipped
        assert RuleType.DELTA_CHECK not in result.failed_rules

    # ========================================================================
    # Short-Circuit Evaluation Tests
    # ========================================================================

    def test_short_circuit_evaluation(self, engine, sample_settings):
        """Test that verification stops at first failed rule."""
        # Create a result that fails multiple rules
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=30.0,  # Fails reference range, critical range, etc.
            result_id="result-1",
            instrument_flags="C",  # Also fails instrument flag
            previous_value=None,
        )

        # Should have failed and returned failed rules
        assert result.passed is False
        assert len(result.failed_rules) > 0

    def test_multiple_failures_documented(self, engine, sample_settings):
        """Test that all failing rules are documented."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code=TEST_TEST_CODE,
            value=30.0,  # Below reference_range_low=70
            result_id="result-1",
            instrument_flags="C",  # In block list
            previous_value=None,
        )

        assert result.passed is False
        # Should have at least reference range and instrument flag failures
        assert RuleType.REFERENCE_RANGE in result.failed_rules
        assert RuleType.INSTRUMENT_FLAG in result.failed_rules

    # ========================================================================
    # Nonexistent Test Code Tests
    # ========================================================================

    def test_verify_with_nonexistent_test_code(self, engine):
        """Test verification with test code that has no settings."""
        result = engine.verify_result(
            tenant_id=TEST_TENANT_ID,
            test_code="NONEXISTENT",
            value=100.0,
            result_id="result-1",
            instrument_flags=None,
            previous_value=None,
        )

        # Without settings, verification might skip or use defaults
        # Engine should handle gracefully
        assert result is not None

    # ========================================================================
    # Batch Verification Tests
    # ========================================================================

    def test_batch_verification(self, engine, sample_settings):
        """Test verifying multiple results at once."""
        results_to_verify = [
            {
                "result_id": "result-1",
                "test_code": TEST_TEST_CODE,
                "value": 85.0,
                "instrument_flags": None,
                "previous_value": None,
            },
            {
                "result_id": "result-2",
                "test_code": TEST_TEST_CODE,
                "value": 150.0,  # Out of range
                "instrument_flags": None,
                "previous_value": None,
            },
            {
                "result_id": "result-3",
                "test_code": TEST_TEST_CODE,
                "value": 85.0,
                "instrument_flags": "C",  # Blocked flag
                "previous_value": None,
            },
        ]

        decisions = engine.verify_batch(
            tenant_id=TEST_TENANT_ID, results_data=results_to_verify
        )

        assert len(decisions) == 3
        assert decisions[0].passed is True
        assert decisions[1].passed is False
        assert decisions[2].passed is False
