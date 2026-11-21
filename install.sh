#!/usr/bin/env bash
# Installe claude-history : lien dans le PATH, fzf si besoin, index construit une fois.
# Relançable sans risque.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bin="${XDG_BIN_HOME:-$HOME/.local/bin}"

say() { printf '  %s\n' "$*"; }

# 1. Lien dans le PATH
mkdir -p "$bin"
ln -sf "$here/claude_history.py" "$bin/claude-history"
say "claude-history -> $bin/claude-history"
case ":$PATH:" in
  *":$bin:"*) ;;
  *) say "Attention : $bin n'est pas dans ton PATH. Ajoute-le à ton shell." ;;
esac

# 2. python3
if ! command -v python3 >/dev/null 2>&1; then
  say "python3 est introuvable : installe-le, c'est la seule vraie dépendance."
  exit 1
fi

# 3. fzf (pour le sélecteur interactif ; sinon un sélecteur Python prend le relais)
if command -v fzf >/dev/null 2>&1; then
  say "fzf : déjà présent"
else
  say "fzf absent : il donne la meilleure expérience (recherche en direct)."
  installer=""
  if   command -v pacman >/dev/null 2>&1; then installer="sudo pacman -S --needed fzf"
  elif command -v apt    >/dev/null 2>&1; then installer="sudo apt install -y fzf"
  elif command -v dnf    >/dev/null 2>&1; then installer="sudo dnf install -y fzf"
  elif command -v zypper >/dev/null 2>&1; then installer="sudo zypper install -y fzf"
  elif command -v brew   >/dev/null 2>&1; then installer="brew install fzf"
  fi
  if [ -n "$installer" ]; then
    printf '  Installer fzf avec « %s » ? [O/n] ' "$installer"
    read -r rep || rep=""
    case "$rep" in
      [nN]*) say "Sauté. claude-history marchera avec son sélecteur Python intégré." ;;
      *) eval "$installer" && say "fzf installé." || say "Échec : installe fzf à la main, le tool marche sans." ;;
    esac
  else
    say "Gestionnaire de paquets non reconnu. Installe fzf à la main (https://github.com/junegunn/fzf)."
    say "Sans fzf, claude-history utilise son sélecteur Python intégré."
  fi
fi

# 4. Complétion shell (Tab)
data="${XDG_DATA_HOME:-$HOME/.local/share}"
bdir="$data/bash-completion/completions"
mkdir -p "$bdir"
install -m644 "$here/completions/claude-history.bash" "$bdir/claude-history"
say "complétion bash : $bdir/claude-history"

zdir="$data/zsh/site-functions"
mkdir -p "$zdir"
install -m644 "$here/completions/_claude-history" "$zdir/_claude-history"
say "complétion zsh : $zdir/_claude-history"
rc="$HOME/.zshrc"
if [ -f "$rc" ] && ! grep -q "claude-history completion" "$rc"; then
  {
    echo ""
    echo "# claude-history completion"
    echo "fpath=(\"$zdir\" \$fpath); autoload -Uz compinit; compinit"
  } >> "$rc"
  say "fpath ajouté à ~/.zshrc (ouvre un nouveau terminal pour l'activer)"
fi

# 5. Construire l'index une fois (silencieux)
say "Construction de l'index de recherche..."
"$here/claude_history.py" search "" >/dev/null 2>&1 || true

say "Terminé. Lance : claude-history (Tab complète les commandes)."
