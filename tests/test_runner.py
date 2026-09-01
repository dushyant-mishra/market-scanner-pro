import unittest
from unittest.mock import patch
import os

import run


class UnifiedRunnerTests(unittest.TestCase):
    def test_every_mode_builds_commands(self):
        for mode in run.MODES:
            commands = run.command_for(mode, port=8765)
            self.assertTrue(commands)
            self.assertTrue(all(command[0] for command in commands))

    def test_live_and_viewer_use_selected_port(self):
        self.assertIn("8765", run.command_for("live", 8765)[0])
        self.assertIn("8765", run.command_for("viewer", 8765)[0])

    def test_default_menu_choice_is_viewer(self):
        with patch("builtins.input", return_value=""):
            self.assertEqual(run.choose_mode(), "viewer")

    def test_failed_step_stops_pipeline(self):
        with patch("run.subprocess.run") as mocked:
            mocked.return_value.returncode = 7
            self.assertEqual(run.run_mode("all"), 7)
            mocked.assert_called_once()

    def test_llm_uses_environment_key_without_prompt(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True), patch("run.getpass.getpass") as prompt:
            self.assertTrue(run.configure_llm(True, "test-model"))
            self.assertEqual(os.environ["OPENAI_REVIEW_MODEL"], "test-model")
            prompt.assert_not_called()

    def test_llm_key_prompt_is_process_only(self):
        with patch.dict(os.environ, {}, clear=True), patch("run.getpass.getpass", return_value="secret"):
            self.assertTrue(run.configure_llm(True))
            self.assertEqual(os.environ["OPENAI_API_KEY"], "secret")


if __name__ == "__main__":
    unittest.main()
