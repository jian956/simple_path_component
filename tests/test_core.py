import unittest

from simple_path_component import (
    ComponentError,
    ComponentResult,
    PathRules,
    POSIX_RULES,
    WINDOWS_RULES,
    validate_component,
    validate_path,
)


class ValidateComponentTests(unittest.TestCase):
    def test_empty_component_is_invalid(self):
        result = validate_component("", POSIX_RULES)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "empty component")
        self.assertEqual(result.component, "")
        self.assertIsNone(result.folded)

    def test_plain_posix_name_is_valid(self):
        result = validate_component("notes.txt", POSIX_RULES)
        self.assertTrue(result.valid)
        self.assertIsNone(result.reason)
        self.assertIsNone(result.folded)

    def test_slash_is_illegal_on_posix(self):
        result = validate_component("a/b", POSIX_RULES)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "illegal character '/'")

    def test_nul_is_illegal_everywhere(self):
        for rules in (POSIX_RULES, WINDOWS_RULES):
            with self.subTest(rules=rules.name):
                result = validate_component("a\x00b", rules)
                self.assertFalse(result.valid)
                self.assertEqual(result.reason, "illegal character '\\x00'")

    def test_length_limit_is_enforced(self):
        too_long = "a" * 256
        result = validate_component(too_long, POSIX_RULES)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "length 256 exceeds 255")

    def test_exactly_at_length_limit_is_valid(self):
        at_limit = "a" * 255
        result = validate_component(at_limit, POSIX_RULES)
        self.assertTrue(result.valid)

    def test_windows_reserved_name(self):
        result = validate_component("CON", WINDOWS_RULES)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "reserved device name")

    def test_windows_reserved_name_with_extension(self):
        result = validate_component("con.txt", WINDOWS_RULES)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "reserved device name")

    def test_windows_reserved_name_is_case_insensitive(self):
        result = validate_component("nul", WINDOWS_RULES)
        self.assertFalse(result.valid)

    def test_windows_illegal_character(self):
        result = validate_component("a:b", WINDOWS_RULES)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "illegal character ':'")

    def test_windows_trailing_dot_is_rejected(self):
        result = validate_component("name.", WINDOWS_RULES)
        self.assertFalse(result.valid)
        self.assertEqual(result.reason, "trailing space or dot is not allowed on Windows")

    def test_windows_trailing_space_is_rejected(self):
        result = validate_component("name ", WINDOWS_RULES)
        self.assertFalse(result.valid)

    def test_case_folding_is_reported_for_windows(self):
        result = validate_component("ReadMe", WINDOWS_RULES)
        self.assertTrue(result.valid)
        self.assertEqual(result.folded, "readme")

    def test_no_case_folding_for_posix(self):
        result = validate_component("ReadMe", POSIX_RULES)
        self.assertTrue(result.valid)
        self.assertIsNone(result.folded)

    def test_non_string_component_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_component(123, POSIX_RULES)

    def test_custom_rules(self):
        rules = PathRules(
            name="custom",
            max_length=3,
            reserved_names=("BAD",),
            illegal_chars="!",
            case_insensitive=False,
        )
        self.assertFalse(validate_component("BAD", rules).valid)
        self.assertFalse(validate_component("a!b", rules).valid)
        self.assertFalse(validate_component("abcd", rules).valid)
        self.assertTrue(validate_component("abc", rules).valid)

    def test_raise_for_error(self):
        result = validate_component("a/b", POSIX_RULES)
        with self.assertRaises(ComponentError) as ctx:
            result.raise_for_error()
        self.assertEqual(ctx.exception.component, "a/b")
        self.assertEqual(ctx.exception.reason, "illegal character '/'")

    def test_raise_for_error_is_noop_when_valid(self):
        result = validate_component("ok", POSIX_RULES)
        self.assertIsNone(result.raise_for_error())


class ValidatePathTests(unittest.TestCase):
    def test_empty_path_yields_no_results(self):
        self.assertEqual(validate_path("", POSIX_RULES), [])

    def test_each_segment_is_checked(self):
        results = validate_path("a/b/c", POSIX_RULES)
        self.assertEqual([r.component for r in results], ["a", "b", "c"])
        self.assertTrue(all(r.valid for r in results))

    def test_invalid_segment_is_reported(self):
        results = validate_path("a//b", POSIX_RULES)
        self.assertEqual([r.valid for r in results], [True, False, True])
        self.assertEqual(results[1].reason, "empty component")

    def test_trailing_separator_yields_empty_component(self):
        results = validate_path("a/", POSIX_RULES)
        self.assertEqual(len(results), 2)
        self.assertFalse(results[1].valid)

    def test_windows_separator(self):
        results = validate_path("a\\b", WINDOWS_RULES, separator="\\")
        self.assertEqual([r.component for r in results], ["a", "b"])

    def test_bad_separator_raises(self):
        with self.assertRaises(ValueError):
            validate_path("a/b", POSIX_RULES, separator="::")

    def test_non_string_path_raises_type_error(self):
        with self.assertRaises(TypeError):
            validate_path(None, POSIX_RULES)

    def test_result_type_is_component_result(self):
        results = validate_path("a", POSIX_RULES)
        self.assertIsInstance(results[0], ComponentResult)


if __name__ == "__main__":
    unittest.main()
