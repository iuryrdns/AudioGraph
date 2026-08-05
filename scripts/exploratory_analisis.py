import pandas as pd
import numpy as np
import scipy.stats as stats

df_small = pd.read_csv("data/small_spotify_tracks_dataset.csv")
df = pd.read_csv("data/spotify_tracks_dataset.csv")


def avaliar_representatividade(df_pop, df_amostra, alpha=0.05):
    relatorio = []

    cols_num = df_pop.select_dtypes(include=[np.number]).columns
    cols_num = [c for c in cols_num if c not in ["Unnamed: 0", "track_id"]]

    for col in cols_num:
        pop_data = df_pop[col].dropna()
        sample_data = df_amostra[col].dropna()

        _, p_val_mean = stats.ttest_ind(pop_data, sample_data, equal_var=False)

        _, p_val_dist = stats.ks_2samp(pop_data, sample_data)

        media_pop = pop_data.mean()
        media_amp = sample_data.mean()
        diff_pct = (
            abs(media_pop - media_amp) / abs(media_pop) * 100 if media_pop != 0 else 0
        )

        relatorio.append(
            {
                "Tipo": "Numérica",
                "Coluna": col,
                "Média População": round(media_pop, 4),
                "Média Amostra": round(media_amp, 4),
                "Diferença (%)": round(diff_pct, 2),
                "p-valor (Média - t-test)": round(p_val_mean, 4),
                "p-valor (Distribuição - KS)": round(p_val_dist, 4),
                "Representativa?": "SIM"
                if (p_val_mean > alpha and p_val_dist > alpha)
                else "NÃO",
            }
        )

    cols_cat = ["explicit", "mode", "key", "time_signature", "track_genre"]
    cols_cat = [c for c in cols_cat if c in df_pop.columns]

    for col in cols_cat:
        pop_freq = df_pop[col].value_counts(normalize=True)
        samp_counts = df_amostra[col].value_counts()

        categories = pop_freq.index
        obs = [samp_counts.get(cat, 0) for cat in categories]
        exp = [pop_freq[cat] * len(df_amostra) for cat in categories]

        chi2_stat, p_val_chi2 = stats.chisquare(f_obs=obs, f_exp=exp)

        relatorio.append(
            {
                "Tipo": "Categórica",
                "Coluna": col,
                "Média População": "-",
                "Média Amostra": "-",
                "Diferença (%)": "-",
                "p-valor (Média - t-test)": "-",
                "p-valor (Distribuição - KS)": round(p_val_chi2, 4),
                "Representativa?": "SIM" if p_val_chi2 > alpha else "NÃO",
            }
        )

    df_relatorio = pd.DataFrame(relatorio)
    return df_relatorio


df_resultado = avaliar_representatividade(df, df_small)
print(df_resultado.to_string(index=False))


import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid")
plt.rcParams["font.sans-serif"] = "DejaVu Sans"

COLOR_POP = "#8EA0B5"
COLOR_SAMP = "#4A5568"

cols_num_plot = [
    "popularity",
    "duration_ms",
    "danceability",
    "energy",
    "loudness",
    "valence",
]

fig, axes = plt.subplots(nrows=2, ncols=3, figsize=(16, 10))
axes = axes.flatten()

for i, col in enumerate(cols_num_plot):
    sns.kdeplot(
        df[col].dropna(),
        ax=axes[i],
        label="População",
        color=COLOR_POP,
        fill=True,
        alpha=0.4,
    )
    sns.kdeplot(
        df_small[col].dropna(),
        ax=axes[i],
        label="Amostra",
        color=COLOR_SAMP,
        linestyle="--",
        linewidth=2,
    )

    axes[i].set_title(f"Distribuição: {col}", fontsize=11, fontweight="bold")
    axes[i].set_xlabel("")
    axes[i].set_ylabel("Densidade")
    axes[i].legend(frameon=True)

fig.suptitle(
    "Comparação Populacional vs. Amostral (Variáveis Numéricas)",
    fontsize=16,
    fontweight="bold",
)
plt.tight_layout()
fig.subplots_adjust(top=0.90)

plt.savefig("data/charts/distribuicao_numericas.png", dpi=300, bbox_inches="tight")
plt.close()


cols_cat_plot = ["explicit", "mode", "key", "time_signature"]

fig, axes = plt.subplots(nrows=2, ncols=2, figsize=(16, 10))
axes = axes.flatten()

for i, col in enumerate(cols_cat_plot):
    df_pop_prop = df[col].value_counts(normalize=True).rename("População").reset_index()
    df_samp_prop = (
        df_small[col].value_counts(normalize=True).rename("Amostra").reset_index()
    )

    df_comp = pd.merge(df_pop_prop, df_samp_prop, on=col).melt(
        id_vars=col, var_name="Grupo", value_name="Proporção"
    )

    sns.barplot(
        data=df_comp,
        x=col,
        y="Proporção",
        hue="Grupo",
        ax=axes[i],
        palette=[COLOR_POP, COLOR_SAMP],
    )
    axes[i].set_title(f"Proporções: {col}", fontsize=11, fontweight="bold")
    axes[i].set_xlabel(col)
    axes[i].set_ylabel("Proporção")
    axes[i].legend(title="")

fig.suptitle(
    "Comparação de Frequências Relativas (Variáveis Categóricas)",
    fontsize=16,
    fontweight="bold",
)
plt.tight_layout()
fig.subplots_adjust(top=0.90)

plt.savefig("data/charts/distribuicao_categoricas.png", dpi=300, bbox_inches="tight")
plt.close()
