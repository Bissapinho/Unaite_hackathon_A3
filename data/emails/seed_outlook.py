"""seed_outlook.py — Pousse les emails de emails.json vers une boîte Outlook via MCP.

Ce script lit `data/emails/emails.json` (généré par build_emails.py) et envoie
chaque email vers une boîte aux lettres Microsoft 365 / Outlook au travers d'un
outil MCP (Model Context Protocol).

NOTE : ce script est PARAMÉTRABLE et n'est PAS destiné à tourner réellement dans
cet environnement de démo (pas d'accès à la boîte ici). Seul le mode --dry-run
fonctionne sans dépendance externe.

PRÉREQUIS (mode réel) :
  - Un serveur MCP Outlook / Microsoft 365 configuré et joignable
    (ex. un serveur MCP exposant un outil "send_mail" / "create_message").
  - Les credentials/permissions adéquats (Mail.Send) côté Microsoft Graph.
  - emails.json présent : lancer d'abord `build_emails.py`.

CONFIG : voir les variables en tête de fichier (ou variables d'environnement
SEED_OUTLOOK_TARGET_MAILBOX, SEED_OUTLOOK_MCP_SERVER, SEED_OUTLOOK_MCP_TOOL).

USAGE :
  # 1) Dry-run : affiche ce qui SERAIT envoyé, sans rien envoyer
  .venv/bin/python data/emails/seed_outlook.py --dry-run

  # 2) Réel (une fois send_via_mcp branché sur le client MCP)
  .venv/bin/python data/emails/seed_outlook.py
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

# --------------------------------------------------------------------------- #
# CONFIGURATION (placeholders — surchargeables via variables d'environnement)
# --------------------------------------------------------------------------- #

# Adresse de la boîte cible vers laquelle pousser les emails.
# Placeholder explicite : à remplacer par la vraie boîte de démo.
TARGET_MAILBOX = os.getenv("SEED_OUTLOOK_TARGET_MAILBOX", "ops@your-tenant.onmicrosoft.com")

# Nom du serveur MCP Outlook / Microsoft 365 (tel que déclaré dans la config MCP).
MCP_SERVER_NAME = os.getenv("SEED_OUTLOOK_MCP_SERVER", "outlook")  # placeholder

# Nom de l'outil MCP qui crée/envoie un message (ex. "send_mail", "create_message").
MCP_TOOL_NAME = os.getenv("SEED_OUTLOOK_MCP_TOOL", "send_mail")  # placeholder

# --------------------------------------------------------------------------- #
# Chemins (relatifs robustes : parents[2] = racine repo)
# --------------------------------------------------------------------------- #
ROOT = pathlib.Path(__file__).resolve().parents[2]
EMAILS_JSON = ROOT / "data" / "emails" / "emails.json"


def load_emails() -> list[dict]:
    """Charge la liste d'emails depuis emails.json (généré par build_emails.py)."""
    if not EMAILS_JSON.exists():
        sys.exit(
            f"[seed_outlook] emails.json introuvable: {EMAILS_JSON}\n"
            f"  -> lance d'abord: .venv/bin/python data/emails/build_emails.py"
        )
    return json.loads(EMAILS_JSON.read_text(encoding="utf-8"))


def send_via_mcp(email: dict) -> None:
    """Envoie UN email vers Outlook via l'outil MCP. Isole l'appel réel.

    TODO: brancher ici le client MCP Outlook réel. Schéma typique :
      1. Ouvrir/réutiliser une connexion au serveur MCP `MCP_SERVER_NAME`.
      2. Appeler l'outil `MCP_TOOL_NAME` avec un payload du type :
             {
                 "to": TARGET_MAILBOX,                 # destinataire (boîte cible)
                 "subject": email["subject"],          # sujet
                 "body": email["body"],                # corps (texte)
                 # optionnel selon l'outil : "from": email["from"], headers, labels...
             }
         Côté Microsoft Graph, cela correspond à créer un `message`
         (subject/body/toRecipients) puis l'envoyer (sendMail).
      3. Vérifier le statut de retour de l'outil et lever en cas d'échec.

    Tant que ce câblage n'est pas fait, on lève proprement.
    """
    raise NotImplementedError(
        "send_via_mcp() n'est pas câblé sur un client MCP Outlook.\n"
        f"  Serveur MCP attendu : {MCP_SERVER_NAME!r}\n"
        f"  Outil MCP attendu   : {MCP_TOOL_NAME!r}\n"
        f"  Boîte cible         : {TARGET_MAILBOX!r}\n"
        "  -> Implémente l'appel dans send_via_mcp() (voir le TODO), "
        "ou relance avec --dry-run pour une simulation sans envoi."
    )


def preview(email: dict) -> None:
    """Affiche ce qui SERAIT envoyé (dry-run) — aucune dépendance externe."""
    body = email.get("body", "")
    excerpt = (body[:120] + "...") if len(body) > 120 else body
    print(f"[DRY-RUN] {email.get('id', '?')}")
    print(f"  from   : {email.get('from', '?')}")
    print(f"  to     : {TARGET_MAILBOX}  (original to: {email.get('to', '?')})")
    print(f"  subject: {email.get('subject', '?')}")
    print(f"  body   : {excerpt}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Affiche ce qui serait envoyé sans appeler send_via_mcp.",
    )
    args = parser.parse_args()

    emails = load_emails()

    if args.dry_run:
        print(f"[seed_outlook] DRY-RUN — {len(emails)} email(s) vers {TARGET_MAILBOX}")
        print(f"[seed_outlook] MCP server={MCP_SERVER_NAME!r} tool={MCP_TOOL_NAME!r}\n")
        for email in emails:
            preview(email)
        print(f"[seed_outlook] DRY-RUN terminé — aucun email envoyé.")
        return

    print(f"[seed_outlook] Envoi de {len(emails)} email(s) vers {TARGET_MAILBOX} via MCP "
          f"({MCP_SERVER_NAME}/{MCP_TOOL_NAME})...")
    for email in emails:
        send_via_mcp(email)
        print(f"  sent: {email.get('id', '?')}")
    print("[seed_outlook] Terminé.")


if __name__ == "__main__":
    main()
