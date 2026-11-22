#!/usr/bin/env bash
# Installe claude-history : lien dans le PATH, fzf si besoin, index construit une fois.
# Relançable sans risque.
set -euo pipefail

src="${BASH_SOURCE[0]:-$0}"
here="$(cd "$(dirname "$src")" 2>/dev/null && pwd || true)"

# Lancé via « curl -fsSL .../install.sh | bash » : pas de fichiers sous la main,
# on clone le dépôt puis on relance l'install depuis la copie.
if [ -z "${here:-}" ] || [ ! -f "$here/claude_history.py" ]; then
  if ! command -v git >/dev/null 2>&1; then
    echo "git est nécessaire pour cette installation." >&2
    exit 1
  fi
  repo="https://github.com/Salemgnk/claude-history.git"
  dest="${XDG_DATA_HOME:-$HOME/.local/share}/claude-history-src"
  echo "Récupération de claude-history dans $dest..."
  if [ -d "$dest/.git" ]; then
    git -C "$dest" pull --ff-only -q || true
  else
    git clone -q "$repo" "$dest"
  fi
  exec bash "$dest/install.sh"
fi

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
