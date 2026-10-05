import os

# Fichiers et dossiers à ignorer
IGNORES = {"__pycache__", ".git", ".venv", "env", "static"}
EXTENSIONS_VOULUES = {".py", ".sql"}  # Ajoutez d'autres extensions si besoin

output_file = "code_complet.txt"

with open(output_file, "w", encoding="utf-8") as outfile:
    for root, dirs, files in os.walk("."):
        # Filtrer les dossiers ignorés
        dirs[:] = [d for d in dirs if d not in IGNORES]

        for file in files:
            ext = os.path.splitext(file)[1]
            if ext in EXTENSIONS_VOULUES and file != "exporter.py":
                filepath = os.path.join(root, file)
                outfile.write(f"\n{'='*50}\n")
                outfile.write(f"FICHIER : {filepath}\n")
                outfile.write(f"{'='*50}\n\n")
                try:
                    with open(filepath, "r", encoding="utf-8") as infile:
                        outfile.write(infile.read())
                except Exception as e:
                    outfile.write(f"Erreur de lecture : {e}\n")

print(f"Terminé ! Tout votre code est dans '{output_file}'.")