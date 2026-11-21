# Maintainer: Salem <https://github.com/Salemgnk>
pkgname=claude-history
pkgver=1.0.0
pkgrel=1
pkgdesc="Retrouver et reprendre une conversation Claude Code depuis le terminal"
arch=('any')
url="https://github.com/Salemgnk/claude-history"
license=('MIT')
depends=('python')
optdepends=('fzf: sélecteur interactif qui se met à jour en direct'
            'ripgrep: recherche plein texte plus rapide')
# Construit depuis le dépôt local (makepkg -si dans le dossier cloné).
# Pour l'AUR, remplacer par une source git ou une archive publiée.
source=()

package() {
  install -Dm755 "$startdir/claude_history.py" "$pkgdir/usr/bin/claude-history"
  install -Dm644 "$startdir/LICENSE" "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
