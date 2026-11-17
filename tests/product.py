#!/usr/bin/env python3
"""End-to-end product workflows, including local issue exports and browser stubs."""

import datetime
import json
import os
from pathlib import Path
import shlex
import stat
import unittest

from regressions import Archive


class ProductArchive(Archive):
    def records(self, command="l", *args, data=None, env=None):
        result = self.cli(command, "--json", *args, data=data, env=env)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def ids(self, command="l", *args, data=None):
        result = self.cli(command, "--ids", *args, data=data)
        self.assertEqual(0, result.returncode, result.stderr)
        return result.stdout.splitlines()


class Views(ProductArchive):
    def setUp(self):
        super().setUp()
        self.a = self.task("Alpha +next +project:ace +owner:anna +due:2030-01-02\n\nVPN in notes\n")
        self.b = self.task("beta +inbox +project:tsk +owner:luca +due:2030-01-01\n", "B002")
        self.c = self.task("Waiting +wait:marco +project:ace\n", "C003")
        self.d = self.task("Legacy backlog +project:ace\n", "D004")
        self.e = self.task(f"Finished +done +completed:{datetime.date.today()} +project:ace +owner:anna\n", "E005")

    def test_group_and_sort_options_can_follow_filters(self):
        result = self.cli("l", "+project:ace", "--group-by", "owner", "--sort", "title")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("OWNER: anna (1)", result.stdout)
        self.assertIn("OWNER: (unassigned) (2)", result.stdout)
        self.assertNotIn("beta", result.stdout)
        self.assertNotIn("Finished", result.stdout)
        self.assertLess(result.stdout.index("Legacy backlog"), result.stdout.index("Waiting"))

    def test_sort_due_places_undated_tasks_last(self):
        records = self.records("l", "--sort", "due")
        self.assertEqual(["B002", "A001", "C003", "D004"], [record["short_id"] for record in records])

    def test_sort_title_is_case_insensitive_and_stable(self):
        self.assertEqual(["Alpha", "beta", "Legacy backlog", "Waiting"], [record["title"] for record in self.records("l", "--sort", "title")])

    def test_projects_and_team_views_include_unassigned_tasks(self):
        self.assertIn("PROJECT: ace (3)", self.cli("projects").stdout)
        self.assertIn("OWNER: (unassigned) (2)", self.cli("team").stdout)
        self.assertEqual(["C003", "D004"], [record["short_id"] for record in self.records("unassigned")])

    def test_multiple_group_values_are_visible_without_duplicate_pipe_actions(self):
        self.task("Shared +project:ace +project:shared\n", "F006")
        result = self.cli("projects")
        self.assertEqual(2, result.stdout.count("[F006]"))
        preview = self.cli("t", "--dry-run", "+next", data=result.stdout)
        self.assertEqual(0, preview.returncode, preview.stderr)
        self.assertEqual(1, preview.stdout.count("[F006]"))
        self.assertIn("5 task(s)", preview.stderr)

    def test_namespace_presence_and_absence_filters(self):
        self.assertEqual(["A001", "B002"], [record["short_id"] for record in self.records("l", "--has", "owner")])
        self.assertEqual(self.ids("unassigned"), self.ids("l", "-+owner:"))
        self.assertEqual(self.ids("unassigned"), self.ids("l", "--without", "owner"))
        self.assertEqual(["A001", "C003", "D004"], [record["short_id"] for record in self.records("l", "+project:ace")])

    def test_json_and_ids_preserve_piped_selection(self):
        selection = self.cli("l", "+project:ace").stdout
        records = self.records("l", data=selection)
        self.assertEqual(["A001", "C003", "D004"], [record["short_id"] for record in records])
        selected_ids = self.ids("l", data=selection)
        self.assertEqual([record["id"] for record in records], selected_ids)
        preview = self.cli("done", "--dry-run", data="\n".join(selected_ids))
        self.assertEqual(0, preview.returncode, preview.stderr)
        self.assertIn("3 task(s)", preview.stderr)

    def test_json_preserves_unicode_quotes_backslashes_and_body_bytes(self):
        title = 'Caffè "quoted" \\path'
        body = '\nNotes\twith\r\ncontrol \x01 and emoji 🐧  \nNo final newline'
        self.a.write_text(title + " +work\n" + body, newline="")
        record = self.records("l", "A001")[0]
        self.assertEqual(title, record["title"])
        self.assertEqual(body, record["body"])
        self.assertEqual(["work"], record["tags"])
        self.assertFalse(record["done"])
        self.assertIsNone(record["due"])
        self.assertIsNone(record["completed"])

    def test_body_search_is_opt_in_and_supports_negation_and_regex(self):
        self.assertEqual([], self.records("l", "VPN"))
        self.assertEqual(["A001"], [record["short_id"] for record in self.records("l", "--body", "vpn")])
        self.assertEqual(["A001"], [record["short_id"] for record in self.records("l", "~vpn|outage", "--body")])
        self.assertEqual(["B002", "C003", "D004"], [record["short_id"] for record in self.records("l", "--body", "-vpn")])
        self.assertEqual([], self.records("l", "--body", "+VPN"))

    def test_empty_machine_output_succeeds(self):
        self.env["TSK_DIR"] = str(self.work / "absent")
        self.assertEqual([], self.records())
        self.assertEqual([], self.ids())
        self.assertFalse((self.work / "absent").exists())

    def test_invalid_options_are_rejected(self):
        for args in [("--sort", "nonsense"), ("--group-by", "bad:key"), ("--sort",), ("--group-by", "owner", "--json"), ("--ids", "--json"), ("--since", "2030-01-02", "--until", "2030-01-01")]:
            with self.subTest(args=args):
                self.assertNotEqual(0, self.cli("l", *args).returncode)


class Workflow(ProductArchive):
    def test_capture_defaults_to_inbox_and_is_visible_in_daily_view(self):
        result = self.cli("a", "Captured", "+project:ace")
        self.assertEqual(0, result.returncode, result.stderr)
        record = self.records("inbox")[0]
        self.assertIn("inbox", record["tags"])
        daily = self.cli().stdout
        self.assertIn("INBOX", daily)
        self.assertIn("Captured", daily)

    def test_explicit_workflow_state_overrides_capture_default(self):
        for state in ["next", "backlog", "wait", "wait:anna", "done"]:
            with self.subTest(state=state):
                result = self.cli("a", "Planned", "+" + state)
                self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual([], self.records("inbox"))
        self.assertEqual(1, len(self.records("next")))
        self.assertEqual(1, len(self.records("backlog")))
        self.assertEqual(2, len(self.records("waiting")))
        self.assertEqual(1, len(self.records("l", "--done")))

    def test_workflow_transitions_are_exclusive_and_keep_project_owner(self):
        self.task("Task +inbox +project:ace +owner:anna\n\nNotes\n")
        for tag, view in [("next", "next"), ("wait:marco", "waiting"), ("backlog", "backlog"), ("inbox", "inbox")]:
            with self.subTest(tag=tag):
                self.assertEqual(0, self.cli("t", "A001", "+" + tag).returncode)
                record = self.records(view)[0]
                states = [item for item in record["tags"] if item in {"inbox", "next", "backlog", "wait"} or item.startswith("wait:")]
                self.assertEqual([tag], states)
                self.assertIn("project:ace", record["tags"])
                self.assertIn("owner:anna", record["tags"])
                self.assertEqual("\nNotes\n", record["body"])

    def test_removing_inbox_moves_task_to_reviewed_backlog(self):
        self.task("Task +inbox\n")
        self.assertEqual(0, self.cli("t", "A001", "-+inbox").returncode)
        self.assertEqual([], self.records("inbox"))
        self.assertEqual(1, len(self.records("backlog")))

    def test_legacy_backlog_is_not_treated_as_unprocessed(self):
        self.task("Previously reviewed task +work\n")
        self.assertEqual([], self.records("inbox"))
        self.assertEqual(1, len(self.records("backlog")))

    def test_waiting_view_and_daily_include_blocker(self):
        self.task("Blocked +wait:marco\n")
        self.assertEqual(1, len(self.records("waiting")))
        daily = self.cli().stdout
        self.assertIn("WAITING", daily)
        self.assertIn("+wait:marco", daily)

    def test_completion_date_is_recorded_and_repeated_done_is_idempotent(self):
        path = self.task("Task +next +project:ace\n")
        self.assertEqual(0, self.cli("done", "A001").returncode)
        first = path.read_bytes()
        record = self.records("l", "--done")[0]
        self.assertEqual(str(datetime.date.today()), record["completed"])
        self.assertNotIn("next", record["tags"])
        self.assertEqual(0, self.cli("done", "A001").returncode)
        self.assertEqual(first, path.read_bytes())

    def test_reopening_removes_completion_date_and_returns_to_inbox(self):
        self.task("Task +done +completed:2026-01-01\n")
        self.assertEqual(0, self.cli("open", "A001").returncode)
        record = self.records("inbox")[0]
        self.assertFalse(record["done"])
        self.assertIsNone(record["completed"])

    def test_tag_done_and_next_transitions_match_lifecycle_commands(self):
        self.task("Task +inbox\n")
        self.assertEqual(0, self.cli("t", "A001", "+done").returncode)
        self.assertTrue(self.records("l", "--all")[0]["done"])
        self.assertEqual(0, self.cli("t", "A001", "+next").returncode)
        record = self.records("next")[0]
        self.assertFalse(record["done"])
        self.assertIsNone(record["completed"])

    def test_completion_dates_are_validated(self):
        self.task("Task +done +completed:2026-02-30\n")
        self.assertNotEqual(0, self.cli("check").returncode)
        self.assertNotEqual(0, self.cli("t", "A001", "+completed:2026-02-30").returncode)

    def test_report_uses_completion_dates_and_excludes_undated_legacy_tasks(self):
        today = datetime.date.today()
        recent = today - datetime.timedelta(days=2)
        old = today - datetime.timedelta(days=20)
        self.task(f"Recent +done +completed:{recent} +owner:anna\n")
        self.task(f"Old +done +completed:{old} +owner:luca\n", "B002")
        self.task("Legacy +done +owner:anna\n", "C003")
        self.assertEqual(["Recent"], [record["title"] for record in self.records("report")])
        self.assertEqual(3, len(self.records("report", "--all-time")))
        self.assertEqual(["Old"], [record["title"] for record in self.records("report", "--since", str(old), "--until", str(old))])
        self.assertIn("OWNER: anna (1)", self.cli("report", "--group-by", "owner").stdout)
        self.assertEqual(0, self.cli("done", "C003").returncode)
        self.assertEqual(["Recent"], [record["title"] for record in self.records("report")])


class DryRun(ProductArchive):
    def test_all_mutations_preview_selection_without_changing_files(self):
        self.task("Alpha +next +due:2030-01-01\n\nNotes\n")
        self.task("Beta +done +completed:2026-01-01\n", "B002")
        before = {path.name: (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode) for path in self.tasks.iterdir()}
        for args, data in [
            (("done", "--dry-run", "A001"), None),
            (("open", "--dry-run", "B002"), None),
            (("due", "--dry-run", "tomorrow", "A001"), None),
            (("due", "--dry-run", "-", "A001"), None),
            (("t", "--dry-run", "A001", "+wait:marco"), None),
            (("t", "--dry-run", "+owner:anna"), "A001\nB002\n"),
            (("d", "--dry-run"), "A001\nB002\n"),
        ]:
            with self.subTest(args=args):
                result = self.cli(*args, data=data)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn("DRY RUN", result.stderr)
                self.assertIn("task(s)", result.stderr)
                self.assertIn("[", result.stdout)
                after = {path.name: (path.read_bytes(), path.stat().st_mtime_ns, path.stat().st_mode) for path in self.tasks.iterdir()}
                self.assertEqual(before, after)

    def test_invalid_dry_run_requests_still_fail(self):
        path = self.task()
        before = path.read_bytes()
        for args in [("due", "--dry-run", "nonsense", "A001"), ("t", "--dry-run", "A001", "+next", "invalid"), ("d", "--dry-run", "unknown")]:
            with self.subTest(args=args):
                self.assertNotEqual(0, self.cli(*args).returncode)
                self.assertEqual(before, path.read_bytes())


class Issues(ProductArchive):
    def setUp(self):
        super().setUp()
        self.path = self.task()

    def test_link_and_replace_preserve_notes_metadata_and_permissions(self):
        self.path.chmod(0o640)
        for key, url in [("ACE-42", "https://example.invalid/issue/42"), ("ACE-43", "https://example.invalid/issue/43?x=(a)&y=b")]:
            result = self.cli("issue", "set", "A001", key, url)
            self.assertEqual(0, result.returncode, result.stderr)
            record = self.records()[0]
            self.assertEqual(["work", "issue:" + key], record["tags"])
            self.assertIn("Notes  \n", record["body"])
            self.assertEqual(1, record["body"].count("Issue: ["))
            self.assertEqual(url + "\n", self.cli("browse", "--print", "A001").stdout)
            self.assertEqual(0o640, stat.S_IMODE(self.path.stat().st_mode))

    def test_link_requires_exact_id_and_http_url(self):
        before = self.path.read_bytes()
        for target, key, url in [("Alpha", "ACE-42", "https://example.invalid/42"), ("A001", "bad:key", "https://example.invalid/42"), ("A001", "ACE-42", "file:///etc/passwd"), ("A001", "ACE-42", "https://example.invalid/has space")]:
            with self.subTest(target=target, key=key, url=url):
                self.assertNotEqual(0, self.cli("issue", "set", target, key, url).returncode)
                self.assertEqual(before, self.path.read_bytes())

    def test_link_preview_does_not_write(self):
        before = self.path.read_bytes()
        result = self.cli("issue", "set", "--dry-run", "A001", "ACE-42", "https://example.invalid/42")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("DRY RUN", result.stdout)
        self.assertEqual(before, self.path.read_bytes())

    def test_link_failure_preserves_original_file(self):
        before = self.path.read_bytes()
        self.shim("cp", "exit 1")
        self.assertNotEqual(0, self.cli("issue", "set", "A001", "ACE-42", "https://example.invalid/42").returncode)
        self.assertEqual(before, self.path.read_bytes())

    def test_browser_receives_the_url_as_one_argument(self):
        url = "https://example.invalid/42?a=1&b=(two)"
        self.assertEqual(0, self.cli("issue", "set", "A001", "ACE-42", url).returncode)
        browser = self.bin / "browser with spaces"
        log = self.work / "browser.log"
        browser.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >"$BROWSER_LOG"\n')
        browser.chmod(0o755)
        self.env.update(BROWSER=shlex.quote(str(browser)), BROWSER_LOG=str(log))
        result = self.cli("browse", "A001")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(url + "\n", log.read_text())

    def test_missing_issue_link_is_an_error(self):
        self.assertNotEqual(0, self.cli("browse", "--print", "A001").returncode)


class Imports(ProductArchive):
    def import_payload(self, payload, *args):
        path = self.work / "import.json"
        path.write_text(json.dumps(payload))
        return self.cli("import", str(path), *args)

    def test_generic_import_preserves_notes_and_is_idempotent(self):
        payload = [{"title": "Imported", "key": "ACE-42", "url": "https://example.invalid/42", "body": "Markdown notes", "project": "ace", "owner": "anna", "tags": ["work"]}]
        first = self.import_payload(payload)
        self.assertEqual(0, first.returncode, first.stderr)
        record = self.records()[0]
        self.assertIn("inbox", record["tags"])
        self.assertIn("owner:anna", record["tags"])
        self.assertIn("Markdown notes", record["body"])
        path = next(self.tasks.glob("*.tsk.md"))
        self.assertEqual(0, self.cli("t", record["id"], "+next").returncode)
        before = path.read_bytes()
        second = self.import_payload(payload)
        self.assertEqual(0, second.returncode, second.stderr)
        self.assertIn("skipped 1", second.stderr)
        self.assertEqual(before, path.read_bytes())
        self.assertEqual(1, len(self.records()))

    def test_stdin_import_and_duplicate_records(self):
        payload = [{"title": "One task", "tags": ["work"]}] * 2
        result = self.cli("import", "-", data=json.dumps(payload))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(1, len(self.records()))

    def test_full_file_is_validated_before_creating_tasks(self):
        for invalid in [{"title": ""}, {"title": "Bad", "tags": ["bad:tag:syntax"]}, {"title": "Bad", "due": "2026-02-30"}, {"title": "Bad", "body": "<<<<<<< HEAD\n"}]:
            with self.subTest(invalid=invalid):
                result = self.import_payload([{"title": "Valid"}, invalid])
                self.assertNotEqual(0, result.returncode)
                self.assertEqual([], list(self.tasks.glob("*.tsk.md")))

    def test_dry_run_does_not_create_archive_or_tasks(self):
        absent = self.work / "absent"
        self.env["TSK_DIR"] = str(absent)
        result = self.import_payload([{"title": "Preview"}], "--dry-run")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("CREATE Preview", result.stdout)
        self.assertFalse(absent.exists())

    def test_import_filters_and_metadata_overrides(self):
        payload = [{"title": "Keep", "project": "ace"}, {"title": "Different", "project": "other"}, {"title": "Closed", "project": "ace", "done": True, "completed": "2026-01-01"}]
        result = self.import_payload(payload, "--only-project", "ace", "--only-open", "--owner", "anna", "--tag", "+work")
        self.assertEqual(0, result.returncode, result.stderr)
        record = self.records()[0]
        self.assertEqual("Keep", record["title"])
        self.assertIn("owner:anna", record["tags"])
        self.assertIn("work", record["tags"])

    def test_gitlab_json_import(self):
        payload = [{"iid": 42, "title": "GitLab task", "web_url": "https://gitlab.example.invalid/group/repo/-/issues/42", "description": "Notes", "project_id": 17, "state": "closed", "closed_at": "2026-01-02T12:30:00Z", "due_date": "2026-01-05", "assignees": [{"username": "anna"}]}]
        result = self.import_payload(payload)
        self.assertEqual(0, result.returncode, result.stderr)
        record = self.records("l", "--done")[0]
        self.assertEqual("2026-01-02", record["completed"])
        self.assertIn("source:gitlab", record["tags"])
        self.assertIn("owner:anna", record["tags"])
        self.assertEqual(0, self.cli("check").returncode)

    def test_jira_json_import_including_rich_description(self):
        payload = {"issues": [{"key": "ACE-42", "self": "https://jira.example.invalid/jira/rest/api/3/issue/123", "fields": {"summary": "Jira task", "description": {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Rich notes"}]}]}, "project": {"key": "ACE"}, "assignee": {"displayName": "Anna Rossi"}, "status": {"statusCategory": {"key": "done"}}, "resolutiondate": "2026-01-02T12:00:00Z"}}]}
        result = self.import_payload(payload)
        self.assertEqual(0, result.returncode, result.stderr)
        record = self.records("l", "--done")[0]
        self.assertIn("Rich notes", record["body"])
        self.assertIn("project:ACE", record["tags"])
        self.assertIn("owner:Anna_Rossi", record["tags"])
        self.assertIn("https://jira.example.invalid/jira/browse/ACE-42", record["body"])

    def test_redmine_json_import_requires_base_and_supports_closed_status_ids(self):
        payload = {"issues": [{"id": 42, "subject": "Redmine task", "description": "Notes", "project": {"name": "ACE Project"}, "assigned_to": {"name": "Anna"}, "status": {"id": 5}}]}
        self.assertNotEqual(0, self.import_payload(payload).returncode)
        self.assertEqual([], self.records())
        result = self.import_payload(payload, "--base-url", "https://redmine.example.invalid", "--closed-status", "5")
        self.assertEqual(0, result.returncode, result.stderr)
        record = self.records("l", "--done")[0]
        self.assertIsNone(record["completed"])
        self.assertIn("https://redmine.example.invalid/issues/42", record["body"])

    def test_tsk_json_export_import_round_trip_preserves_ids_tags_and_body(self):
        path = self.task('Original +project:ace +done +completed:2026-01-01\n\nNotes  \nNo final newline')
        original = path.read_bytes()
        exported = self.records("l", "--all")
        restored = self.work / "restored"
        restored.mkdir()
        self.env["TSK_DIR"] = str(restored)
        result = self.import_payload(exported)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(original, (restored / path.name).read_bytes())
        self.assertEqual(0, self.cli("check").returncode)

    def test_existing_ids_are_preserved_and_never_overwritten(self):
        path = self.task()
        exported = self.records("l", "--all")
        exported[0]["title"] = "Changed remotely"
        original = path.read_bytes()
        result = self.import_payload(exported)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("skipped 1", result.stderr)
        self.assertEqual(original, path.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
