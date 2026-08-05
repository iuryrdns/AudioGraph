uv run python -m scripts.evaluate \
    --rebuild \
    --count 10 \
    --seed-index 0 \
    --random-seed 42 \
    --output-csv data/relatorio.csv \
    --num-samples 100

uv run python -m scripts.analyze_results