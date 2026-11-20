"""Tests de la version terminal de claude-history.

Lancer : python3 -m unittest discover -s ~/.local/share/claude-history/tests -v
"""
import sys
sys.dont_write_bytecode = True
import contextlib
import importlib.machinery
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

SCRIPT = os.environ.get("CLAUDE_HISTORY", str(Path(__file__).resolve().parent.parent / "claude-history"))


def load():
    loader = importlib.machinery.SourceFileLoader("claude_history", SCRIPT)
    spec = importlib.util.spec_from_loader("claude_history", loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


mod = load()


def rec(kind, ts, uid, content, cwd, **extra):
    message = {"role": kind, "content": content}
    if kind == "assistant":
        message["model"] = "claude-test"
    return {"type": kind, "timestamp": ts, "uuid": uid, "cwd": cwd, "message": message, **extra}


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = Path(self.tmp)
        cwd_a = str(self.root / "vpn maison")
        os.mkdir(cwd_a)
        ta, tb = "2026-11-16T12:14:00Z", "2026-11-10T12:00:00Z"
        self.write("proj-a", "aaa", [
            {"type": "ai-title", "aiTitle": "Règles pare-feu WireGuard"},
            rec("user", ta, "u1", "pourquoi mon peer WireGuard ne ping pas"
                "<system-reminder>secret</system-reminder>", cwd_a),
            rec("assistant", ta, "a1", [
                {"type": "thinking", "thinking": "pensée cachée"},
                {"type": "tool_use", "name": "Bash", "id": "t1", "input": {"command": "nft list ruleset"}},
            ], cwd_a),
            rec("user", ta, "u2", [{"type": "tool_result", "tool_use_id": "t1", "content": "sortie cachée"}], cwd_a),
            rec("assistant", ta, "a2", [{"type": "text", "text": "Ta règle forward bloque le réseau."}], cwd_a),
            rec("user", ta, "u3", "wireguard meta", cwd_a, isMeta=True),
            rec("assistant", ta, "a3", [{"type": "text", "text": "wireguard sidechain"}], cwd_a, isSidechain=True),
        ])
        self.write("proj-b", "bbb", [
            rec("user", tb, "u4", 'il a dit "bonjour" au\tréseau\nlocal', "/chemin/disparu"),
            rec("assistant", tb, "a4", [{"type": "text", "text": "D'accord."}], "/chemin/disparu"),
        ])
        saved = mod.ROOT, mod.CACHE_FILE
        self.addCleanup(lambda: (setattr(mod, "ROOT", saved[0]), setattr(mod, "CACHE_FILE", saved[1]), mod.CACHE.clear()))
        mod.ROOT = self.root
        mod.CACHE_FILE = self.root / "cache" / "index.json"
        mod.CACHE.clear()

    def write(self, project, sid, records):
        d = self.root / project
        d.mkdir()
        with open(d / f"{sid}.jsonl", "w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")


class TestText(Case):
    def test_actions_label(self):
        self.assertEqual(mod.actions_label(Counter({"Bash": 2, "Read": 1})), "3 actions : Bash ×2, Read")
        self.assertEqual(mod.actions_label(Counter({"Bash": 1})), "1 action : Bash")

    def test_list_lines_order_and_fields(self):
        lines = list(mod.list_lines())
        self.assertEqual([l.split("\t")[:2] for l in lines], [["proj-a", "aaa"], ["proj-b", "bbb"]])
        self.assertIn("Règles pare-feu WireGuard", lines[0])
        self.assertIn("vpn maison", lines[0])
        self.assertIn("16 nov.", lines[0])
        self.assertIn("1 msg", lines[0])

    def test_list_line_is_sanitized(self):
        line = list(mod.list_lines())[1]
        self.assertEqual(line.count("\t"), 2)
        self.assertNotIn("\n", line)
        self.assertIn('il a dit "bonjour" au réseau local', line)

    def test_write_text(self):
        buf = io.StringIO()
        mod.write_text(self.root / "proj-a" / "aaa.jsonl", buf)
        t = buf.getvalue()
        for want in ("Règles pare-feu WireGuard", "Toi", "pourquoi mon peer WireGuard ne ping pas",
                     "Claude", "1 action : Bash", "Ta règle forward bloque le réseau."):
            self.assertIn(want, t)
        for hidden in ("secret", "pensée cachée", "sortie cachée", "meta", "sidechain"):
            self.assertNotIn(hidden, t)

    def test_write_text_survives_broken_pipe(self):
        class Closed:
            def write(self, s):
                raise BrokenPipeError
        mod.write_text(self.root / "proj-a" / "aaa.jsonl", Closed())  # ne lève rien


class TestSearch(Case):
    def ids(self, q):
        return [(s["id"], len(h)) for s, h in mod.search_hits(q)]

    def test_search_case_insensitive_and_filtered(self):
        self.assertEqual(self.ids("wireguard"), [("aaa", 1)])   # ni meta ni sidechain

    def test_search_accents(self):
        self.assertEqual(self.ids("RÉSEAU"), [("aaa", 1), ("bbb", 1)])

    def test_search_query_with_quote(self):
        self.assertEqual(self.ids('dit "bonjour"'), [("bbb", 1)])

    def test_search_too_short(self):
        self.assertEqual(mod.search_hits("a"), [])
        self.assertEqual(list(mod.search_lines(" ")), list(mod.list_lines()))

    def test_search_without_rg(self):
        with mock.patch.object(mod.shutil, "which", return_value=None):
            self.assertEqual(self.ids("wireguard"), [("aaa", 1)])

    def test_search_lines(self):
        (line,) = list(mod.search_lines("forward"))
        self.assertEqual(line.split("\t")[:2], ["proj-a", "aaa"])
        self.assertIn("1 passage", line)
        self.assertIn("Ta règle forward bloque", line)

    def test_write_hits(self):
        buf = io.StringIO()
        mod.write_hits(self.root / "proj-a" / "aaa.jsonl", "forward", buf)
        self.assertIn("Claude", buf.getvalue())
        self.assertIn("\033[7mforward\033[0m", buf.getvalue())


class TestCli(Case):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mod.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_list_and_search_commands(self):
        code, out, _ = self.run_main("list")
        self.assertEqual((code, len(out.splitlines())), (0, 2))
        code, out, _ = self.run_main("search", "ping", "pas")
        self.assertEqual((code, out.split("\t")[1]), (0, "aaa"))

    def test_list_empty_root(self):
        mod.ROOT = self.root / "absent"
        mod.CACHE.clear()
        self.assertEqual(self.run_main("list")[:2], (0, ""))
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("Aucune conversation", err)

    def test_preview_modes(self):
        with mock.patch.dict(os.environ, {"FZF_PROMPT": "titre> "}):
            self.assertIn("1 action : Bash", self.run_main("preview", "proj-a", "aaa", "forward")[1])
        with mock.patch.dict(os.environ, {"FZF_PROMPT": "texte> "}):
            out = self.run_main("preview", "proj-a", "aaa", "forward")[1]
        self.assertIn("\033[7mforward", out)
        self.assertNotIn("1 action", out)

    def test_show_rejects_bad_ids(self):
        self.assertEqual(self.run_main("show", "../etc", "passwd")[0], 1)
        code, _, err = self.run_main("show", "proj-a", "zzz")
        self.assertEqual(code, 1)
        self.assertIn("n'existe plus", err)

    def test_help_and_unknown(self):
        self.assertEqual(self.run_main("--help")[0], 0)
        self.assertEqual(self.run_main("nimporte")[0], 2)

    def test_web_routing(self):
        with mock.patch.object(mod, "serve") as serve:
            mod.main(["8788", "--no-open"])
            mod.main(["web"])
        self.assertEqual(serve.call_args_list, [mock.call(8788, False), mock.call(8787, True)])

    def test_toggle_action(self):
        to_text = mod.toggle_action("titre> ", "ME")
        self.assertIn("change-prompt(texte> )", to_text)
        self.assertIn("reload(ME search {q})", to_text)
        back = mod.toggle_action("texte> ", "ME")
        self.assertIn("change-prompt(titre> )", back)
        self.assertIn("reload(ME list)", back)

    def test_resume_command_quotes(self):
        info = {"cwd": "/tmp/vpn maison", "id": "aaa"}
        self.assertEqual(mod.resume_command(info), "cd '/tmp/vpn maison' && claude --resume aaa")

    def test_resume_missing_dir(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err), mock.patch.object(mod.os, "execvp") as ex:
            code = mod.resume({"cwd": "/chemin/disparu", "id": "bbb"})
        self.assertEqual(code, 1)
        ex.assert_not_called()
        self.assertIn("cd /chemin/disparu && claude --resume bbb", err.getvalue())

    def test_resume_execs_in_cwd(self):
        cwd = str(self.root / "vpn maison")
        with mock.patch.object(mod.shutil, "which", return_value="/usr/bin/claude"), \
             mock.patch.object(mod.os, "chdir") as cd, mock.patch.object(mod.os, "execvp") as ex:
            mod.resume({"cwd": cwd, "id": "aaa"})
        cd.assert_called_once_with(cwd)
        ex.assert_called_once_with("claude", ["claude", "--resume", "aaa"])

    def test_pick_without_fzf(self):
        with mock.patch.object(mod.shutil, "which", return_value=None):
            code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("fzf est introuvable", err)


if __name__ == "__main__":
    unittest.main()
