#!/usr/bin/env python3
"""Black-box regression tests; only Python's standard library is required."""

import datetime
import errno
import os
from pathlib import Path
import pty
import select
import shlex
import shutil
import signal
import stat
import subprocess
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parent.parent
TSK = Path(os.environ.get("TSK_BIN", ROOT / "tsk")).resolve()


class Archive(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="tsk-regression-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)
        self.tasks = self.work / "tasks"
        self.tasks.mkdir()
        self.tmp = self.work / "tmp"
        self.tmp.mkdir()
        self.bin = self.work / "bin"
        self.bin.mkdir()
        self.env = {
            **os.environ,
            "TSK_DIR": str(self.tasks),
            "TMPDIR": str(self.tmp),
            "PATH": f"{self.bin}:{ROOT}:{os.environ['PATH']}",
        }

    def task(self, text="Alpha +work\n\nNotes  \n", suffix="A001"):
        path = self.tasks / f"20261117090000000-{suffix}.tsk.md"
        path.write_text(text)
        return path

    def run_program(self, argv, data=None, env=None, timeout=10):
        stdin = {"stdin": subprocess.DEVNULL} if data is None else {"input": data}
        return subprocess.run(
            [str(arg) for arg in argv],
            **stdin,
            env=env or self.env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def cli(self, *args, **kwargs):
        return self.run_program([TSK, *args], **kwargs)

    def shim(self, name, script):
        real = shutil.which(name)
        path = self.bin / name
        path.write_text(f"#!/bin/sh\n{script}\nexec {shlex.quote(real)} \"$@\"\n")
        path.chmod(0o755)
        return path

    def editor(self):
        path = self.work / "editor with spaces"
        path.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >"$EDITOR_LOG"\n')
        path.chmod(0o755)
        self.env["EDITOR"] = str(path)
        self.env["EDITOR_LOG"] = str(self.work / "editor.log")
        return path

    def terminal(self, argv, reply=None, prompt=b"(y/n)?"):
        pid, fd = pty.fork()
        if pid == 0:
            os.execvpe(str(argv[0]), [str(arg) for arg in argv], self.env)
        output = bytearray()
        status = None
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                ready, _, _ = select.select([fd], [], [], 0.05)
                if ready:
                    try:
                        chunk = os.read(fd, 65536)
                        if not chunk:
                            break
                        output.extend(chunk)
                        if reply is not None and prompt in output:
                            os.write(fd, reply)
                            reply = None
                    except OSError as error:
                        if error.errno != errno.EIO:
                            raise
                        break
                child, status = os.waitpid(pid, os.WNOHANG)
                if child:
                    break
                status = None
            if status is None:
                child, status = os.waitpid(pid, os.WNOHANG)
                if not child:
                    os.kill(pid, signal.SIGKILL)
                    os.waitpid(pid, 0)
                    self.fail("terminal command timed out")
            return os.waitstatus_to_exitcode(status), output.decode(errors="replace")
        finally:
            os.close(fd)


class Core(Archive):
    def test_exact_and_negative_tags_do_not_match_prefixes(self):
        self.task()
        self.task("Beta +workflow\n", "B002")
        self.assertEqual("[A001] Alpha +work\n", self.cli("l", "+work").stdout)
        self.assertEqual("[B002] Beta +workflow\n", self.cli("l", "-+work").stdout)

    def test_regex_escapes_preserve_literal_punctuation(self):
        self.task("Review config.txt +work\n")
        self.task("Review configXtxt +home\n", "B002")
        result = self.cli("l", r"~\.txt")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("[A001] Review config.txt +work\n", result.stdout)
        self.assertEqual("", result.stderr)

    def test_literal_backslashes_are_preserved(self):
        self.task("Review C:\\temp +work\n")
        self.assertEqual("[A001] Review C:\\temp +work\n", self.cli("l", r"C:\temp").stdout)

    def test_filter_errors_propagate_without_changes(self):
        path = self.task()
        original = path.read_bytes()
        for command in [("l",), ("r",), ("s",), ("e",), ("done",), ("open",), ("due", "tomorrow"), ("d",)]:
            for invalid in ["+bad:tag:syntax", "~[", "~"]:
                with self.subTest(command=command, invalid=invalid):
                    result = self.cli(*command, invalid)
                    self.assertNotEqual(0, result.returncode)
                    self.assertEqual(original, path.read_bytes())

    def test_bad_regex_is_rejected_even_after_an_empty_selection(self):
        self.task()
        self.assertNotEqual(0, self.cli("l", "absent", "~[").returncode)

    def test_temporary_file_failure_propagates(self):
        path = self.task()
        original = path.read_bytes()
        result = self.cli("done", "A001", env={**self.env, "TMPDIR": str(self.work / "absent")})
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(original, path.read_bytes())
        self.assertNotIn("tsk: done\n", result.stderr)

    @unittest.skipIf(os.geteuid() == 0, "root bypasses ordinary file permissions")
    def test_readonly_mutations_fail_without_success_messages(self):
        path = self.task()
        original = path.read_bytes()
        path.chmod(0o400)
        for command, data in [(('done', 'A001'), None), (('open', 'A001'), None), (('due', 'tomorrow', 'A001'), None), (('t', '+next'), 'A001\n')]:
            with self.subTest(command=command):
                result = self.cli(*command, data=data)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(original, path.read_bytes())
                self.assertNotIn("tags updated", result.stderr)

    def test_failed_replacement_preserves_the_original(self):
        path = self.task()
        original = path.read_bytes()
        self.shim("mv", 'case "$*" in *"/.tsk.edit."*) exit 1 ;; esac')
        result = self.cli("done", "A001")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(original, path.read_bytes())
        self.assertEqual([], list(self.tasks.glob(".tsk.edit.*")))
        self.assertNotIn("tsk: done\n", result.stderr)

    def test_failed_header_generation_preserves_the_original(self):
        path = self.task()
        original = path.read_bytes()
        self.shim("awk", 'case "$*" in *"action=add"*) exit 1 ;; esac')
        result = self.cli("done", "A001")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(original, path.read_bytes())
        self.assertEqual([], list(self.tasks.glob(".tsk.edit.*")))

    def test_failed_body_copy_preserves_the_original(self):
        path = self.task()
        original = path.read_bytes()
        self.shim("tail", "exit 1")
        result = self.cli("done", "A001")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(original, path.read_bytes())

    def test_failed_permission_copy_preserves_the_original(self):
        path = self.task()
        original = path.read_bytes()
        self.shim("cp", "exit 1")
        result = self.cli("done", "A001")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(original, path.read_bytes())

    def test_failed_capture_does_not_create_a_partial_task(self):
        self.shim("cat", "exit 1")
        result = self.cli("a", "New task", data="Notes\n")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], list(self.tasks.iterdir()))

    def test_tag_updates_preserve_body_bytes_and_mode(self):
        path = self.task()
        body = b"\nNotes with trailing spaces  \n\nNo final newline"
        path.write_bytes(b"Alpha +work\n" + body)
        group = next((group for group in os.getgroups() if group != path.stat().st_gid), path.stat().st_gid)
        os.chown(path, -1, group)
        path.chmod(0o640)
        owner = path.stat().st_uid
        result = self.cli("done", "A001")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(f"Alpha +work +done +completed:{datetime.date.today()}\n".encode() + body, path.read_bytes())
        self.assertEqual(0o640, stat.S_IMODE(path.stat().st_mode))
        self.assertEqual(owner, path.stat().st_uid)
        self.assertEqual(group, path.stat().st_gid)

    def test_symlink_updates_are_rejected_without_changing_the_target(self):
        target = self.work / "external.md"
        target.write_text("External task +work\n")
        path = self.tasks / "20261117090000000-A001.tsk.md"
        path.symlink_to(target)
        self.assertNotEqual(0, self.cli("done", "A001").returncode)
        self.assertTrue(path.is_symlink())
        self.assertEqual("External task +work\n", target.read_text())

    def test_concurrent_writers_keep_both_changes(self):
        path = self.task()
        real_awk = shlex.quote(shutil.which("awk"))
        self.env["REVIEW_BARRIER"] = str(self.work)
        self.shim("awk", f'''
case "$*" in *"action=add"*)
    {real_awk} "$@" || exit 1
    touch "$REVIEW_BARRIER/$REVIEW_WORKER.ready"
    if [ "$REVIEW_WORKER" = first ]; then
        while [ ! -e "$REVIEW_BARRIER/release" ]; do sleep 0.01; done
    fi
    exit 0
    ;;
esac''')
        processes = []
        try:
            for worker in ["first", "second"]:
                process = subprocess.Popen(
                    [str(TSK), "t", "+" + worker],
                    env={**self.env, "REVIEW_WORKER": worker},
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, start_new_session=True,
                )
                processes.append(process)
                process.stdin.write("A001\n")
                process.stdin.close()
                process.stdin = None
                deadline = time.monotonic() + (5 if worker == "first" else 0.3)
                while not (self.work / f"{worker}.ready").exists() and time.monotonic() < deadline:
                    time.sleep(0.01)
                if worker == "first":
                    self.assertTrue((self.work / "first.ready").exists(), "first writer did not reach the update")
            (self.work / "release").touch()
            for process in processes:
                _, error = process.communicate(timeout=5)
                self.assertEqual(0, process.returncode, error)
            self.assertEqual("Alpha +work +first +second\n\nNotes  \n", path.read_text())
        finally:
            for process in processes:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()

    def test_quoted_metadata_is_normalized_and_deduplicated(self):
        result = self.cli("a", "Quoted title +work +due:tomorrow", "+work")
        self.assertEqual(0, result.returncode, result.stderr)
        paths = list(self.tasks.glob("*.tsk.md"))
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        self.assertEqual(f"Quoted title +work +due:{tomorrow} +inbox\n", paths[0].read_text())
        self.assertEqual(0, self.cli("check").returncode)

    def test_invalid_headers_never_create_tasks(self):
        for args in [("   ",), ("\t",), ("First\nSecond",), ("Task +bad:tag:format",), ("Task +due:2026-02-30",), ("Task +due:tomorrow +due:friday",)]:
            with self.subTest(args=args):
                self.assertNotEqual(0, self.cli("a", *args).returncode)
                self.assertEqual([], list(self.tasks.glob("*.tsk.md")))

    def test_all_tag_changes_are_validated_before_writing(self):
        path = self.task()
        original = path.read_bytes()
        for args in [("+next", "-invalid"), ("+next", "+bad:tag:format"), ("+next", "+due:2026-02-30")]:
            with self.subTest(args=args):
                self.assertNotEqual(0, self.cli("t", *args, data="A001\n").returncode)
                self.assertEqual(original, path.read_bytes())

    def test_valid_tag_change_order_is_preserved(self):
        path = self.task()
        result = self.cli("t", "+next", "-+work", "+due:tomorrow", "-+next", data="A001\n")
        self.assertEqual(0, result.returncode, result.stderr)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        self.assertEqual(f"Alpha +due:{tomorrow}\n\nNotes  \n", path.read_text())

    def test_check_rejects_conflict_markers_in_header_and_body(self):
        for text in ["<<<<<<< HEAD\nAlpha\n=======\nBeta\n>>>>>>> branch\n", "Alpha\n\n<<<<<<< HEAD\nNotes\n=======\nOther\n>>>>>>> branch\n", "Alpha\n\n||||||| base\n"]:
            with self.subTest(text=text):
                self.task(text)
                result = self.cli("check")
                self.assertNotEqual(0, result.returncode)
                self.assertIn("unresolved merge conflict", result.stdout)

    def test_check_preserves_valid_markdown_and_plain_due_tags(self):
        self.task("Alpha +due\n\nHeading\n=======\n")
        self.assertEqual(0, self.cli("check").returncode)

    def test_check_validates_calendar_dates(self):
        for date, valid in [("2024-02-29", True), ("2000-02-29", True), ("1900-02-29", False), ("2026-02-29", False), ("2026-04-31", False), ("2026-00-01", False), ("2026-12-32", False), ("tomorrow", False)]:
            with self.subTest(date=date):
                self.task(f"Alpha +due:{date}\n")
                self.assertEqual(valid, self.cli("check").returncode == 0)

    def test_check_rejects_empty_titles_invalid_tags_duplicates_and_ids(self):
        for text in ["", "\n", "+work\n", "Alpha +bad:tag:format\n", "Alpha +work +work\n", "Alpha +due:2026-10-01 +due:2026-10-02\n"]:
            with self.subTest(text=text):
                self.task(text)
                self.assertNotEqual(0, self.cli("check").returncode)
        self.task("Alpha\n")
        (self.tasks / "invalid id.tsk.md").write_text("Beta\n")
        self.assertNotEqual(0, self.cli("check").returncode)

    def test_empty_archive_is_healthy(self):
        result = self.cli("check")
        self.assertEqual(0, result.returncode)
        self.assertEqual("ok: no problems found\n", result.stdout)

    def test_matching_directory_does_not_hide_regular_tasks(self):
        (self.tasks / "000.tsk.md").mkdir()
        self.task()
        self.assertEqual("[A001] Alpha +work\n", self.cli("l").stdout)

    def test_check_handles_a_large_archive(self):
        for index in range(1000):
            self.task(f"Task {index} +work +due:2028-02-29\n", f"T{index:04d}")
        result = self.cli("check", timeout=10)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_editor_accepts_a_program_path_containing_spaces(self):
        path = self.task()
        self.editor()
        result = self.cli("e", "A001")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(f"{path}\n", (self.work / "editor.log").read_text())

    def test_editor_arguments_and_task_paths_remain_separate(self):
        self.tasks = self.work / "tasks with 'quotes; $(false)"
        self.tasks.mkdir()
        self.env["TSK_DIR"] = str(self.tasks)
        path = self.task()
        editor = self.editor()
        self.env["EDITOR"] = f"{shlex.quote(str(editor))} --wait"
        result = self.cli("e", "A001", data="A001\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(f"--wait\n{path}\n", (self.work / "editor.log").read_text())

    def test_piped_editor_and_fzf_callback_receive_a_terminal(self):
        self.task()
        editor = self.work / "tty-editor"
        editor.write_text('#!/bin/sh\n[ -t 0 ] && [ -t 1 ] || exit 91\nprintf "editor has a terminal\\n"\n')
        editor.chmod(0o755)
        self.env["EDITOR"] = str(editor)
        for argv in [["sh", "-c", f"printf 'A001\\n' | {shlex.quote(str(TSK))} e"], [ROOT / "tsk-fzf", "__edit", "A001"]]:
            with self.subTest(argv=argv):
                status, output = self.terminal(argv)
                self.assertEqual(0, status, output)
                self.assertIn("editor has a terminal", output)

    def test_piped_deletion_only_removes_selected_tasks(self):
        selected = self.task()
        other = self.task("Beta +home\n", "B002")
        result = self.cli("d", data="A001\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(selected.exists())
        self.assertTrue(other.exists())

    def test_interactive_deletion_requires_confirmation(self):
        path = self.task()
        status, output = self.terminal([TSK, "d", "A001"], reply=b"n\n")
        self.assertNotEqual(0, status, output)
        self.assertIn("delete 1 task(s) (y/n)?", output)
        self.assertTrue(path.exists())

    def test_interactive_deletion_accepts_confirmation(self):
        path = self.task()
        status, output = self.terminal([TSK, "d", "A001"], reply=b"y\n")
        self.assertEqual(0, status, output)
        self.assertFalse(path.exists())


class TagCatalogue(Archive):
    def setUp(self):
        super().setUp()
        self.task("Alpha +work +project:ace +owner:anna\n\nBody mentions +ghost\n")
        self.task("Beta +work +work +project:tsk +owner:luca\n", "B002")
        self.task("Finished +work +project:ace +owner:anna +done\n", "C003")

    def test_default_counts_open_tasks_once_per_tag_in_alphabetical_order(self):
        result = self.cli("tags")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "+owner:anna\t1\n+owner:luca\t1\n+project:ace\t1\n+project:tsk\t1\n+work\t2\n",
            result.stdout,
        )

    def test_all_includes_completed_tasks(self):
        result = self.cli("tags", "--all")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(
            "+done\t1\n+owner:anna\t2\n+owner:luca\t1\n+project:ace\t2\n+project:tsk\t1\n+work\t3\n",
            result.stdout,
        )

    def test_done_only_counts_completed_tasks(self):
        result = self.cli("tags", "--done")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("+done\t1\n+owner:anna\t1\n+project:ace\t1\n+work\t1\n", result.stdout)

    def test_namespace_matches_the_exact_key(self):
        self.task("Other +project +project_extra:test\n", "D004")
        result = self.cli("tags", "project")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("+project:ace\t1\n+project:tsk\t1\n", result.stdout)

    def test_names_omit_counts_and_compose_with_namespace_and_status(self):
        result = self.cli("tags", "--all", "--names", "project")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("+project:ace\n+project:tsk\n", result.stdout)

    def test_piped_selection_narrows_counts(self):
        selection = self.cli("l", "+project:ace").stdout
        result = self.cli("tags", data=selection)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("+owner:anna\t1\n+project:ace\t1\n+work\t1\n", result.stdout)

    def test_completed_piped_selection_uses_the_requested_mode(self):
        result = self.cli("tags", "--all", "project", data="A001\nC003\nC003\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("+project:ace\t2\n", result.stdout)

    def test_case_variants_remain_visible(self):
        self.task("Different spelling +Work\n", "D004")
        self.assertIn("+Work\t1\n", self.cli("tags").stdout)
        self.assertIn("+work\t2\n", self.cli("tags").stdout)

    def test_unknown_namespace_or_empty_selection_is_empty(self):
        self.assertEqual("", self.cli("tags", "unknown").stdout)
        self.assertEqual("", self.cli("tags", data="").stdout)

    def test_invalid_arguments_are_rejected(self):
        for args in [("--unknown",), ("project", "owner"), ("project:ace",), ("",)]:
            with self.subTest(args=args):
                self.assertNotEqual(0, self.cli("tags", *args).returncode)

    def test_catalogue_errors_propagate(self):
        self.shim("awk", "exit 1")
        result = self.cli("tags")
        self.assertNotEqual(0, result.returncode)
        self.assertEqual("", result.stdout)

    def test_missing_archive_is_empty_and_is_not_created(self):
        self.env["TSK_DIR"] = str(self.work / "absent")
        result = self.cli("tags")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stdout)
        self.assertFalse((self.work / "absent").exists())


class DirectTags(Archive):
    def setUp(self):
        super().setUp()
        self.path = self.task()
        self.other = self.task("Beta mentions A001 +home\n", "B002")

    def test_short_id_changes_only_the_exact_task(self):
        other = self.other.read_bytes()
        result = self.cli("t", "A001", "+next", "-+work")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("Alpha +next\n\nNotes  \n", self.path.read_text())
        self.assertEqual(other, self.other.read_bytes())

    def test_full_id_is_accepted(self):
        result = self.cli("t", self.path.name.removesuffix(".tsk.md"), "+due:tomorrow")
        self.assertEqual(0, result.returncode, result.stderr)
        tomorrow = datetime.date.today() + datetime.timedelta(days=1)
        self.assertIn(f"+due:{tomorrow}", self.path.read_text())

    def test_explicit_id_takes_precedence_over_stdin(self):
        original = self.path.read_bytes()
        result = self.cli("t", "B002", "+next", data="A001\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(original, self.path.read_bytes())
        self.assertIn("+next", self.other.read_text())

    def test_unknown_partial_empty_and_title_selectors_never_modify_tasks(self):
        original = self.path.read_bytes()
        other = self.other.read_bytes()
        for target in ["unknown", "A00", "Alpha", "", "A001\\n"]:
            with self.subTest(target=target):
                result = self.cli("t", target, "+next", data="A001\n")
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(original, self.path.read_bytes())
                self.assertEqual(other, self.other.read_bytes())

    def test_colliding_suffix_requires_a_full_id(self):
        collision = self.tasks / "20261117090100000-A001.tsk.md"
        collision.write_text("Collision +work\n")
        self.assertNotEqual(0, self.cli("t", "A001", "+next").returncode)
        self.assertEqual("Alpha +work\n\nNotes  \n", self.path.read_text())
        result = self.cli("t", self.path.name.removesuffix(".tsk.md"), "+next")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("Collision +work\n", collision.read_text())

    def test_completed_tasks_can_be_updated(self):
        self.path.write_text("Alpha +done\n")
        result = self.cli("t", "A001", "+owner:anna")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("Alpha +done +owner:anna\n", self.path.read_text())

    def test_entire_request_is_validated_before_updating(self):
        original = self.path.read_bytes()
        for changes in [(), ("+next", "-invalid"), ("+next", "+due:2026-02-30")]:
            with self.subTest(changes=changes):
                self.assertNotEqual(0, self.cli("t", "A001", *changes).returncode)
                self.assertEqual(original, self.path.read_bytes())

    def test_changes_without_id_still_require_a_piped_selection(self):
        self.assertNotEqual(0, self.cli("t", "+next").returncode)
        result = self.cli("t", "+next", data="A001\nB002\n")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("+next", self.path.read_text())
        self.assertIn("+next", self.other.read_text())


class BashCompletion(Archive):
    def setUp(self):
        super().setUp()
        self.task("Alpha +work +project:ace\n")
        self.task("Finished +home +project:old +done\n", "B002")
        self.completion = ROOT / "completions" / "tsk.bash"

    def complete(self, *words, wordbreaks=":"):
        script = r'''
set -eu
source "$1"
shift
cd "$TMPDIR"
COMP_WORDBREAKS=$1
before=$COMP_WORDBREAKS
shift
COMP_WORDS=("$@")
COMP_CWORD=$((${#COMP_WORDS[@]}-1))
_tsk_complete
[[ $COMP_WORDBREAKS == "$before" ]] || exit 99
if ((${#COMPREPLY[@]})); then printf '%s\n' "${COMPREPLY[@]}"; fi
'''
        result = self.run_program(["bash", "--noprofile", "--norc", "-c", script, "bash", self.completion, wordbreaks, *words])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        return result.stdout.splitlines()

    def test_commands_include_the_catalogue_and_installed_extensions(self):
        extension = self.bin / "tsk-hello"
        extension.write_text("#!/bin/sh\nexit 0\n")
        extension.chmod(0o755)
        replies = self.complete("tsk", "")
        self.assertIn("tags", replies)
        self.assertIn("hello", replies)
        self.assertIn("fzf", replies)
        self.assertEqual(len(replies), len(set(replies)))

    def test_command_prefix(self):
        self.assertEqual(["tags"], self.complete("tsk", "ta"))

    def test_existing_tags_and_builtins_are_completed(self):
        self.assertEqual({"+work", "+wait"}, set(self.complete("tsk", "a", "Fix", "+w")))
        self.assertEqual(["+next"], self.complete("tsk", "t", "A001", "+n"))
        self.assertEqual({"-+work", "-+wait"}, set(self.complete("tsk", "t", "A001", "-+w")))
        self.assertIn("-+work", self.complete("tsk", "t", "A001", "-"))

    def test_namespace_values_are_trimmed_for_readline(self):
        self.assertEqual(["ace"], self.complete("tsk", "l", "+project", ":", "ac"))
        self.assertEqual(["ace", "old"], self.complete("tsk", "l", "+project", ":"))
        self.assertEqual(["ace"], self.complete("tsk", "t", "A001", "-+project", ":", "a"))

    def test_namespace_values_work_without_colon_word_breaks(self):
        self.assertEqual(["+project:ace"], self.complete("tsk", "l", "+project:ac", wordbreaks=""))

    def test_completion_after_a_namespaced_filter_starts_a_new_argument(self):
        replies = self.complete("tsk", "l", "+project", ":", "ace", "")
        self.assertIn("+work", replies)
        self.assertIn("A001", replies)

    def test_task_ids_follow_command_status_modes(self):
        for words, expected in [
            (("l", "A"), ["A001"]), (("l", "B"), []),
            (("l", "--all", "B"), ["B002"]), (("l", "--done", "B"), ["B002"]),
            (("open", "B"), ["B002"]), (("done", "A"), ["A001"]),
            (("t", "B"), ["B002"]), (("e", "B"), ["B002"]),
            (("due", "tomorrow", "B"), ["B002"]),
        ]:
            with self.subTest(words=words):
                self.assertEqual(expected, self.complete("tsk", *words))

    def test_catalogue_completes_namespace_keys_once(self):
        self.assertEqual(["project"], self.complete("tsk", "tags", "pro"))
        self.assertEqual([], self.complete("tsk", "tags", "project", ""))

    def test_command_options_are_contextual(self):
        self.assertEqual({"--all", "--done", "--body", "--ids", "--json", "--group-by", "--sort", "--has", "--without", "--since", "--until", "--all-time"}, set(self.complete("tsk", "l", "--")))
        self.assertEqual({"--all", "--done", "--names"}, set(self.complete("tsk", "tags", "--")))
        self.assertIn("--sort", self.complete("tsk", "l", "+work", "--"))

    def test_product_views_and_option_values_are_completed(self):
        commands = self.complete("tsk", "")
        for command in ["inbox", "next", "waiting", "backlog", "projects", "team", "unassigned", "report", "browse", "import", "issue", "g"]:
            self.assertIn(command, commands)
        self.assertEqual(["project"], self.complete("tsk", "l", "--group-by", "pro"))
        self.assertEqual(["completed"], self.complete("tsk", "report", "--sort", "comp"))
        self.assertEqual(["--dry-run"], self.complete("tsk", "t", "--dry"))
        self.assertEqual(["A001"], self.complete("tsk", "t", "--dry-run", "A"))
        self.assertEqual(["A001"], self.complete("tsk", "projects", "A"))
        self.assertEqual(["gitlab"], self.complete("tsk", "import", "--source", "gitl"))
        self.assertEqual(["set"], self.complete("tsk", "issue", "se"))

    def test_due_date_suggestions_and_unfinished_due_tag(self):
        self.assertEqual(["tomorrow"], self.complete("tsk", "due", "tom"))
        self.assertEqual([], self.complete("tsk", "a", "Title", "+due", ":"))

    def test_malformed_ids_are_not_completed_or_evaluated(self):
        (self.tasks / 'evil$(touch${IFS}completion-owned).tsk.md').write_text("Malformed ID\n")
        self.assertEqual([], self.complete("tsk", "e", "evil"))
        self.assertFalse((self.tmp / "completion-owned").exists())

    def test_empty_archive_still_completes_commands_and_builtin_tags(self):
        self.env["TSK_DIR"] = str(self.work / "absent")
        self.assertIn("tags", self.complete("tsk", ""))
        self.assertEqual(["+next"], self.complete("tsk", "a", "Title", "+n"))
        self.assertFalse((self.work / "absent").exists())

    def test_real_tab_insertion_preserves_namespaces_and_due_prefix(self):
        rc = self.work / "bashrc"
        rc.write_text(r'''
source "$COMPLETION_SCRIPT"
_capture() {
    printf '%s\n' "$READLINE_LINE" >"$COMPLETION_LOG"
    READLINE_LINE=exit
    READLINE_POINT=4
}
bind -x '"\C-x\C-r":_capture'
PS1='completion> '
''')
        log = self.work / "readline.log"
        self.env["COMPLETION_SCRIPT"] = str(self.completion)
        self.env["COMPLETION_LOG"] = str(log)
        for line, expected in [
            ("tsk l +project:ac", "tsk l +project:ace "),
            ("tsk t A001 -+project:ac", "tsk t A001 -+project:ace "),
            ("tsk a Fix +du", "tsk a Fix +due:"),
        ]:
            with self.subTest(line=line):
                status, output = self.terminal(
                    ["bash", "--noprofile", "--rcfile", rc, "-i"],
                    reply=line.encode() + b"\t\x18\x12\n", prompt=b"completion> ",
                )
                self.assertEqual(0, status, output)
                self.assertEqual(expected + "\n", log.read_text())


class Fzf(Archive):
    def setUp(self):
        super().setUp()
        selector = self.bin / "fake-fzf"
        selector.write_text("#!/bin/sh\nsed -n '1p'\n")
        selector.chmod(0o755)
        self.env["TSK_FZF_FZF"] = str(selector)

    def test_selection_preserves_list_format(self):
        self.task()
        result = self.run_program([ROOT / "tsk-fzf", "+work"])
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("[A001] Alpha +work\n", result.stdout)

    def test_filter_failure_is_not_reported_as_an_empty_selection(self):
        self.task()
        result = self.run_program([ROOT / "tsk-fzf", "-f", "~["])
        self.assertEqual(1, result.returncode, result.stderr)


class GitSync(Archive):
    def setUp(self):
        super().setUp()
        self.env = {key: value for key, value in self.env.items() if not key.startswith("GIT_")}
        self.env.update({
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_AUTHOR_NAME": "Tests", "GIT_AUTHOR_EMAIL": "tests@example.invalid",
            "GIT_COMMITTER_NAME": "Tests", "GIT_COMMITTER_EMAIL": "tests@example.invalid",
            "GIT_TERMINAL_PROMPT": "0", "GIT_MERGE_AUTOEDIT": "no",
        })
        self.remote = self.work / "remote.git"
        self.git(self.work, "init", "--bare", "--initial-branch=main", self.remote)
        self.git(self.tasks, "init", "--initial-branch=main")
        self.git(self.tasks, "remote", "add", "origin", self.remote)
        self.path = self.task()
        self.commit("initial")
        self.git(self.tasks, "push", "-u", "origin", "main")
        self.other = self.work / "other"
        self.git(self.work, "clone", self.remote, self.other)

    def git(self, directory, *args):
        result = self.run_program(["git", "-C", directory, *args])
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result.stdout.strip()

    def commit(self, message, directory=None):
        directory = directory or self.tasks
        self.git(directory, "add", "-A")
        self.git(directory, "commit", "-m", message)

    def sync(self):
        return self.run_program([ROOT / "tsk-y"])

    def conflicting_remote_change(self):
        self.path.write_text("Alpha +work +next\n\nNotes\n")
        (self.other / self.path.name).write_text("Alpha +work +done\n\nNotes\n")
        self.commit("remote changes", self.other)
        self.git(self.other, "push")
        return self.git(self.remote, "rev-parse", "main")

    def test_clean_archive_downloads_remote_changes(self):
        (self.other / "20261117090100000-B002.tsk.md").write_text("Remote task +home\n")
        self.commit("new remote task", self.other)
        self.git(self.other, "push")
        result = self.sync()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertTrue((self.tasks / "20261117090100000-B002.tsk.md").exists())

    def test_clean_archive_pushes_an_existing_local_commit(self):
        self.path.write_text("Alpha +work +next\n")
        self.commit("previous attempt")
        result = self.sync()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(self.git(self.tasks, "rev-parse", "HEAD"), self.git(self.remote, "rev-parse", "main"))

    def test_divergent_changes_merge_without_global_pull_configuration(self):
        (self.other / "20261117090100000-B002.tsk.md").write_text("Remote task\n")
        self.commit("remote changes", self.other)
        self.git(self.other, "push")
        self.path.write_text("Alpha +next\n")
        result = self.sync()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual("Alpha +next\n", self.path.read_text())
        self.assertTrue((self.tasks / "20261117090100000-B002.tsk.md").exists())

    def test_retry_never_commits_or_publishes_unresolved_conflicts(self):
        remote_head = self.conflicting_remote_change()
        self.assertNotEqual(0, self.sync().returncode)
        conflicted = self.path.read_bytes()
        self.assertIn(b"<<<<<<<", conflicted)
        result = self.sync()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(conflicted, self.path.read_bytes())
        self.assertTrue(self.git(self.tasks, "diff", "--name-only", "--diff-filter=U"))
        self.assertEqual(remote_head, self.git(self.remote, "rev-parse", "main"))
        self.assertNotEqual(0, self.cli("check").returncode)

    def test_staged_resolution_requires_finishing_the_merge(self):
        self.conflicting_remote_change()
        self.assertNotEqual(0, self.sync().returncode)
        self.path.write_text("Resolved task +work\n")
        self.git(self.tasks, "add", self.path.name)
        result = self.sync()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("finish the current Git operation", result.stderr)

    def test_conflict_markers_are_rejected_before_staging(self):
        head = self.git(self.tasks, "rev-parse", "HEAD")
        self.path.write_text("Alpha\n\n<<<<<<< HEAD\nNotes\n=======\nOther\n>>>>>>> branch\n")
        self.assertNotEqual(0, self.sync().returncode)
        self.assertEqual(head, self.git(self.tasks, "rev-parse", "HEAD"))
        self.assertEqual("", self.git(self.tasks, "diff", "--cached", "--name-only"))

    def test_nested_archive_cannot_commit_unrelated_files(self):
        nested = self.tasks / "nested"
        nested.mkdir()
        (nested / self.path.name).write_text("Nested task\n")
        (self.tasks / "unrelated.txt").write_text("Outside the task directory\n")
        head = self.git(self.tasks, "rev-parse", "HEAD")
        self.env["TSK_DIR"] = str(nested)
        result = self.sync()
        self.assertNotEqual(0, result.returncode)
        self.assertIn("root of its Git repository", result.stderr)
        self.assertEqual(head, self.git(self.tasks, "rev-parse", "HEAD"))
        self.assertEqual("", self.git(self.tasks, "diff", "--cached", "--name-only"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
