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
            rec("assistant", ta, "a5", [{"type": "text", "text": "Bonjour encore, on brainstorme l'ui/ux."}], cwd_a),
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


class TestFind(Case):
    def ids(self, q):
        return [l.split("\t")[1] for l in mod.search_lines(q)]

    def test_fold_keeps_length(self):
        for s in ("RÉSEAU", "Œuvre ﬁnale İstanbul", "ça déjà vu", "plain ascii"):
            self.assertEqual(len(mod.fold(s)), len(s))
        self.assertEqual(mod.fold("RÉSEAU déjà"), "reseau deja")

    def test_words_in_any_order(self):
        self.assertEqual(self.ids("bloque forward"), ["aaa"])
        self.assertEqual(self.ids("forward   bloque"), ["aaa"])
        self.assertEqual(self.ids("forward bonjour-inexistant"), [""])

    def test_accents_both_ways(self):
        self.assertEqual(sorted(self.ids("reseau")), ["aaa", "bbb"])
        self.assertEqual(sorted(self.ids("RÉSEAU")), ["aaa", "bbb"])
        self.assertEqual(self.ids("REGLE"), ["aaa"])

    def test_prefix_and_partial_words(self):
        self.assertEqual(self.ids("brainstorm ui"), ["aaa"])
        self.assertEqual(self.ids("wiregu"), ["aaa"])

    def test_matches_start_of_words_only(self):
        self.assertEqual(self.ids("ward"), [""])          # pas le milieu de « forward »
        self.assertEqual(self.ids("ux"), ["aaa"])         # « ui/ux » : après une barre oblique
        self.assertEqual(self.ids("feu"), ["aaa"])        # « pare-feu » : après un tiret

    def test_passages_prefer_lines_with_every_word(self):
        idx = mod.refresh_index(write=False)
        e = idx[str(self.root / "proj-a" / "aaa.jsonl")]
        e["o"] += "\nforward seul"
        e["f"] += "\nforward seul"
        e["r"] += "a"
        self.assertIn("1 passage", next(mod.search_lines("forward bloque", idx)))  # la ligne qui a les deux
        self.assertIn("2 passages", next(mod.search_lines("forward", idx)))
        self.assertIn("2 passages", next(mod.search_lines("bonjour bloque", idx)))  # aucune ligne n'a les deux

    def test_title_or_folder_ranked_first(self):
        # bbb (plus ancienne) a « bonjour » dans son titre, aaa (plus récente) seulement dans un message
        self.assertEqual(self.ids("bonjour"), ["bbb", "aaa"])
        self.assertEqual(self.ids("maison"), ["aaa"])  # nom du dossier

    def test_hidden_text_not_searched(self):
        for q in ("secret", "cachée", "sidechain", "meta"):
            self.assertEqual(self.ids(q), [""], q)

    def test_counts_and_tail(self):
        line = next(mod.search_lines("forward"))
        self.assertIn("1 passage", line)
        self.assertIn("Ta règle forward bloque", line)

    def test_empty_query_lists_all(self):
        self.assertEqual(list(mod.search_lines("")), list(mod.list_lines()))
        self.assertEqual(list(mod.search_lines("   ")), list(mod.list_lines()))

    def test_no_result_placeholder(self):
        (line,) = list(mod.search_lines("zzzz"))
        self.assertTrue(line.startswith("\t\t"))
        self.assertIn("Aucune conversation ne contient « zzzz »", line)

    def test_index_refreshes_when_file_changes(self):
        mod.refresh_index()
        self.assertEqual(self.ids("nouveauté"), [""])
        with open(self.root / "proj-b" / "bbb.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(rec("assistant", "2026-11-11T09:00:00Z", "a9",
                                   [{"type": "text", "text": "une nouveauté ici"}], "/chemin/disparu")) + "\n")
        mod.refresh_index()
        self.assertEqual(self.ids("nouveaute"), ["bbb"])
        self.assertIn(str(self.root / "proj-b" / "bbb.jsonl"), json.loads(mod.text_file().read_text()))

    def test_caches_are_private(self):
        mod.refresh_index()
        for f in (mod.text_file(), mod.CACHE_FILE):
            self.assertEqual(f.stat().st_mode & 0o077, 0, f)

    def test_home_path_does_not_match_every_folder(self):
        with mock.patch.object(mod, "HOME", self.tmp):
            mod.refresh_index()
            self.assertEqual(self.ids(Path(self.tmp).name), [""])
            self.assertEqual(self.ids("maison"), ["aaa"])

    def test_index_from_older_version_is_rebuilt(self):
        idx = mod.refresh_index()
        for e in idx.values():
            e.pop("v", None)
            e["f"] = e["o"] = "vieux"
        mod.text_file().write_text(json.dumps(idx))
        mod.refresh_index()
        self.assertEqual(self.ids("forward"), ["aaa"])

    def test_index_survives_corrupt_file(self):
        mod.text_file().parent.mkdir(parents=True, exist_ok=True)
        mod.text_file().write_text("{pas du json")
        self.assertEqual(self.ids("forward"), ["aaa"])


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

    def test_preview_with_and_without_query(self):
        self.assertIn("1 action : Bash", self.run_main("preview", "proj-a", "aaa")[1])
        self.assertIn("1 action : Bash", self.run_main("preview", "proj-a", "aaa", " ")[1])
        out = self.run_main("preview", "proj-a", "aaa", "FORWARD bloque")[1]
        self.assertIn("1 passage", out)
        self.assertIn("\033[7mforward\033[0m \033[7mbloque\033[0m", out)
        self.assertNotIn("1 action", out)

    def test_preview_title_only_match_shows_conversation(self):
        out = self.run_main("preview", "proj-a", "aaa", "pare-feu")[1]
        self.assertIn("1 action : Bash", out)

    def test_placeholder_is_silent(self):
        self.assertEqual(self.run_main("preview", "", "", "zzzz"), (0, "", ""))
        self.assertEqual(self.run_main("show", "", ""), (0, "", ""))
        placeholder = list(mod.search_lines("zzzz"))[0]
        done = mock.Mock(returncode=0, stdout=placeholder + "\n")
        with mock.patch.object(mod.shutil, "which", return_value="/usr/bin/fzf"), \
             mock.patch.object(mod.subprocess, "run", return_value=done), \
             mock.patch.object(mod, "resume") as res:
            self.assertEqual(self.run_main(), (0, "", ""))
        res.assert_not_called()

    def test_query_command_is_read_only(self):
        code, out, _ = self.run_main("query", "forward")
        self.assertEqual((code, out.split("\t")[1]), (0, "aaa"))
        self.assertFalse(mod.text_file().exists())
        self.run_main("search", "forward")
        self.assertTrue(mod.text_file().exists())

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

    def test_fzf_args_single_mode(self):
        args = mod.fzf_args("ME")
        self.assertIn("--disabled", args)
        self.assertIn("--bind=change:reload:ME query {q}", args)
        self.assertFalse(any("ctrl-f" in a or "toggle" in a for a in args))

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

    def test_pick_falls_back_without_fzf(self):
        with mock.patch.object(mod.shutil, "which", return_value=None), \
             mock.patch.object(mod, "pick_plain", return_value=0) as pp:
            self.assertEqual(self.run_main()[0], 0)
        pp.assert_called_once()


class TestExtras(Case):
    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = mod.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_last_resumes_most_recent(self):
        with mock.patch.object(mod, "resume", return_value=0) as res:
            code = mod.main(["last"])
        self.assertEqual(code, 0)
        self.assertEqual(res.call_args[0][0]["id"], "aaa")  # la plus récente

    def test_last_without_conversations(self):
        mod.ROOT = self.root / "absent"
        mod.CACHE.clear()
        code, _, err = self.run_main("last")
        self.assertEqual(code, 1)
        self.assertIn("Aucune", err)

    def test_export_markdown(self):
        code, out, _ = self.run_main("export", "proj-a", "aaa")
        self.assertEqual(code, 0)
        self.assertIn("# Règles pare-feu WireGuard", out)
        self.assertIn("## Toi", out)
        self.assertIn("## Claude", out)
        self.assertIn("Ta règle forward bloque le réseau.", out)
        self.assertIn("_[1 action : Bash]_", out)
        self.assertNotIn("\x1b[", out)  # aucun code couleur
        for hidden in ("secret", "pensée cachée", "sortie cachée", "sidechain", "wireguard meta"):
            self.assertNotIn(hidden, out)

    def test_export_bad_id(self):
        self.assertEqual(self.run_main("export", "../etc", "passwd")[0], 1)
        self.assertEqual(self.run_main("export", "proj-a", "zzz")[0], 1)

    def test_stats(self):
        code, out, _ = self.run_main("stats")
        self.assertEqual(code, 0)
        self.assertIn("2 conversations", out)
        self.assertIn("vpn maison", out)

    def test_stats_empty(self):
        mod.ROOT = self.root / "absent"
        mod.CACHE.clear()
        self.assertEqual(self.run_main("stats")[0], 0)

    def test_found_sessions(self):
        self.assertEqual([s["id"] for s in mod.found_sessions("")], ["aaa", "bbb"])  # récentes d'abord
        self.assertEqual([s["id"] for s in mod.found_sessions("wiregu")], ["aaa"])
        self.assertEqual(mod.found_sessions("zzzz"), [])

    def test_pick_plain_resumes_by_number(self):
        answers = iter(["wiregu", "1"])
        with mock.patch.object(mod, "resume", return_value=0) as res:
            code = mod.pick_plain(read=lambda p="": next(answers))
        self.assertEqual(code, 0)
        self.assertEqual(res.call_args[0][0]["id"], "aaa")

    def test_pick_plain_refines_then_quits(self):
        answers = iter(["pas-de-resultat", "wireguard", ""])  # requête, requête, Entrée = quitter
        with mock.patch.object(mod, "resume") as res:
            code = mod.pick_plain(read=lambda p="": next(answers))
        self.assertEqual(code, 0)
        res.assert_not_called()

    def test_pick_plain_bad_number_asks_again(self):
        answers = iter(["99", ""])  # numéro hors liste puis Entrée
        with mock.patch.object(mod, "resume") as res:
            code = mod.pick_plain(read=lambda p="": next(answers))
        self.assertEqual(code, 0)
        res.assert_not_called()

    def test_pick_uses_fallback_without_fzf(self):
        with mock.patch.object(mod.shutil, "which", return_value=None), \
             mock.patch.object(mod, "pick_plain", return_value=0) as pp:
            self.assertEqual(mod.pick(), 0)
        pp.assert_called_once()

    def test_install_script(self):
        sh = (Path(SCRIPT).parent / "install.sh").read_text()
        self.assertIn(".local/bin", sh)
        self.assertIn("claude-history", sh)
        for pm in ("pacman", "apt", "dnf", "brew"):
            self.assertIn(pm, sh)
        self.assertIn("fzf", sh)


if __name__ == "__main__":
    unittest.main()
