#!/usr/bin/env python3
"""
Tests for query_must_filter.py output buffer integration.

Verifies that filtering diagnostics are captured in RAGOutput buffer
when provided, and fall back to print() when not provided.
"""

import pytest
from src.query.query_must_filter import satisfies_query_must
from src.utils.rag_output import RAGOutput


class TestQueryMustFilterOutputIntegration:
    """Test RAGOutput buffer integration in query_must_filter."""

    def test_output_buffer_captures_contain_one_of_failure(self):
        """Verify contain_one_of failure is logged to output buffer."""
        query = "What is a fighter?"
        query_must = {
            "contain_one_of": [
                ["cleric", "clerics"],  # Fails - neither term present
                ["armor class 6", "ac 6"],
            ]
        }
        output = RAGOutput()

        result = satisfies_query_must(query, query_must, debug=True, output=output)

        assert result == False, "Should fail validation"
        assert len(output.diagnostics) == 1, "Should log one diagnostic message"
        assert "Failed contain_one_of" in output.diagnostics[0]
        assert "cleric" in output.diagnostics[0]

    def test_output_buffer_captures_contain_all_of_failure(self):
        """Verify contain_all_of failure is logged to output buffer."""
        query = "psionic blast"
        query_must = {
            "contain_all_of": ["psionic", "attack"]  # Fails - missing "attack"
        }
        output = RAGOutput()

        result = satisfies_query_must(query, query_must, debug=True, output=output)

        assert result == False
        assert len(output.diagnostics) == 1
        assert "Failed contain_all_of" in output.diagnostics[0]
        assert "attack" in output.diagnostics[0]

    def test_output_buffer_captures_contain_failure(self):
        """Verify contain failure is logged to output buffer."""
        query = "magic missile"
        query_must = {"contain": "psionic"}  # Fails - "psionic" not present
        output = RAGOutput()

        result = satisfies_query_must(query, query_must, debug=True, output=output)

        assert result == False
        assert len(output.diagnostics) == 1
        assert "Failed contain" in output.diagnostics[0]
        assert "psionic" in output.diagnostics[0]

    def test_output_buffer_captures_contain_range_failure(self):
        """Verify contain_range failure is logged to output buffer."""
        query = "intelligence 8 psionic blast"
        query_must = {
            "contain_range": {"min": 10, "max": 13}  # Fails - 8 not in [10, 13]
        }
        output = RAGOutput()

        result = satisfies_query_must(query, query_must, debug=True, output=output)

        assert result == False
        assert len(output.diagnostics) == 1
        assert "Failed contain_range" in output.diagnostics[0]
        assert "10" in output.diagnostics[0] and "13" in output.diagnostics[0]

    def test_no_diagnostics_when_debug_false(self):
        """Verify no diagnostics are logged when debug=False."""
        query = "fighter"
        query_must = {"contain": "cleric"}  # Fails
        output = RAGOutput()

        result = satisfies_query_must(query, query_must, debug=False, output=output)

        assert result == False
        assert len(output.diagnostics) == 0, "Should not log when debug=False"

    def test_no_diagnostics_when_validation_passes(self):
        """Verify no diagnostics are logged when all validations pass."""
        query = "7th level cleric attacking armor class 6"
        query_must = {
            "contain_one_of": [["cleric", "clerics"], ["armor class 6", "ac 6"]]
        }
        output = RAGOutput()

        result = satisfies_query_must(query, query_must, debug=True, output=output)

        assert result == True
        assert len(output.diagnostics) == 0, "Should not log on success"

    def test_backward_compatibility_without_output_buffer(self):
        """Verify function still works when output buffer not provided."""
        query = "fighter"
        query_must = {"contain": "cleric"}  # Fails

        # Should not raise - falls back to print()
        result = satisfies_query_must(query, query_must, debug=True, output=None)

        assert result == False

    def test_multiple_failures_logged(self):
        """Verify first failure is logged (short-circuit AND logic)."""
        query = "some random text"
        query_must = {
            "contain_one_of": [["cleric"]],  # Fails first
            "contain_all_of": ["fighter"],  # Would also fail
            "contain": "magic",  # Would also fail
        }
        output = RAGOutput()

        result = satisfies_query_must(query, query_must, debug=True, output=output)

        assert result == False
        assert len(output.diagnostics) == 1, "Only first failure logged (short-circuit)"
        assert "Failed contain_one_of" in output.diagnostics[0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
