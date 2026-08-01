import argparse
import csv
import os
import time

from scripts.search_api import search_download


def main():
    parser = argparse.ArgumentParser(description="Baixa previews de áudio via iTunes API")
    parser.add_argument("csv_path", help="Caminho para o CSV do dataset")
    parser.add_argument("--n", type=int, default=300, help="Quantidade de faixas a processar (0 = todas)")
    parser.add_argument("--saida", default="data/audios", help="Pasta onde salvar os áudios")
    parser.add_argument("--delay", type=float, default=0.5, help="Segundos de espera entre requisições")
    args = parser.parse_args()

    os.makedirs(args.saida, exist_ok=True)

    with open(args.csv_path, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        linhas = list(leitor)

    if args.n and args.n > 0:
        linhas = linhas[: args.n]

    log_path = os.path.join(args.saida, "baixados.csv")
    log_existe = os.path.exists(log_path)
    log_file = open(log_path, "a", newline="", encoding="utf-8")
    log_writer = csv.writer(log_file)
    if not log_existe:
        log_writer.writerow(["track_id", "artists", "track_name", "status"])

    total = len(linhas)
    sucesso = 0
    for i, linha in enumerate(linhas, 1):
        track_id = linha.get("track_id")
        artista = (linha.get("artists") or "").split(";")[0]
        musica = linha.get("track_name") or ""

        destino = os.path.join(args.saida, f"{artista} - {musica}.m4a")
        if os.path.exists(destino):
            print(f"[{i}/{total}] {artista} - {musica}: já existe, pulando")
            continue

        status = search_download(artista, musica, destino)
        if status == "sucesso":
            sucesso += 1
        print(f"[{i}/{total}] {artista} - {musica}: {status}")
        log_writer.writerow([track_id, artista, musica, status])

        time.sleep(args.delay)

    log_file.close()
    print(f"\nConcluído: {sucesso}/{total} prévias baixadas em '{args.saida}'")
    print(f"Log completo em: {log_path}")


if __name__ == "__main__":
    main()
