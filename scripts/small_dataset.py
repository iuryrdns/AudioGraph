import pandas as pd

PATH_DATASET = "../data/spotify_tracks_dataset.csv"
OUTPUT_PATH_SMALL_DATASET = "../data/small_spotify_tracks_dataset.csv"

df = pd.read_csv(PATH_DATASET)

df_small = df.sample(n=1000)

df_small.to_csv(OUTPUT_PATH_SMALL_DATASET, index=False)
