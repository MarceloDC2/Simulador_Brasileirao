import streamlit as st
import requests
from random import random
import pandas as pd
import matplotlib.pyplot as plt
import time
import Utilidades

# ---------- Configurações iniciais ----------
PASTA_SAIDA = None  # Não usado no app web, mantido para compatibilidade
RODADA_FINAL = 38

# ---------- Funções utilitárias (baseadas no seu código) ----------

def pega_times(ano, sleep_between_requests=0.25):
    """Pega a lista de times a partir da rodada 1 da API da Gazeta."""
    url_basica = f'https://footstats.gazetaesportiva.com/campeonatos/brasileiro-serie-a-{ano}/partidas/rodada/'
    times = dict()
    url = url_basica + '1'
    resp = requests.get(url)
    resp.raise_for_status()
    dados = resp.json()

    def pega_um_time(nome):
        times[Utilidades.LimpaTexto(nome)] = {
            'partidas_mandante': 0,
            'vitorias_mandante': 0,
            'empates_mandante': 0,
            'derrotas_mandante': 0,
            'partidas_visitante': 0,
            'vitorias_visitante': 0,
            'empates_visitante': 0,
            'derrotas_visitante': 0,
            'pontos': 0.0,
        }

    for i in range(10):
        pega_um_time(dados[i]['equipe_mandante']['nome'])
        pega_um_time(dados[i]['equipe_visitante']['nome'])
    time.sleep(sleep_between_requests)
    return times


class JogosNaoRealizados:
    def __init__(self):
        self.jogos = []  # cada item: [mandante, visitante, prob_man, prob_vis_cumul, prob_total_cumul]


def preenche_times_e_jogos(times, ano, rodada_inicial=1, sleep_between_requests=0.25):
    jogos_faltantes = JogosNaoRealizados()
    url_basica = f'https://footstats.gazetaesportiva.com/campeonatos/brasileiro-serie-a-{ano}/partidas/rodada/'

    for rodada in range(rodada_inicial, RODADA_FINAL + 1):
        url = url_basica + str(rodada)
        resp = requests.get(url)
        resp.raise_for_status()
        dados = resp.json()

        for jogo in range(10):
            mandante = Utilidades.LimpaTexto(dados[jogo]['equipe_mandante']['nome'])
            visitante = Utilidades.LimpaTexto(dados[jogo]['equipe_visitante']['nome'])

            if dados[jogo]['partidaEncerrada'] == True:
                placar = dados[jogo]['placar']
                empate = placar['empate']
                vitoria_mandante = placar['vitoriaMandante']

                times[mandante]['partidas_mandante'] += 1
                times[visitante]['partidas_visitante'] += 1

                if empate:
                    times[mandante]['empates_mandante'] += 1
                    times[mandante]['pontos'] += 1
                    times[visitante]['empates_visitante'] += 1
                    times[visitante]['pontos'] += 1
                elif vitoria_mandante:
                    times[mandante]['vitorias_mandante'] += 1
                    times[mandante]['pontos'] += 3.01
                    times[visitante]['derrotas_visitante'] += 1
                else:
                    times[mandante]['derrotas_mandante'] += 1
                    times[visitante]['vitorias_visitante'] += 1
                    times[visitante]['pontos'] += 3.01
            else:
                jogos_faltantes.jogos.append([mandante, visitante, 0.0, 0.0, 0.0])
        time.sleep(sleep_between_requests)
    return times, jogos_faltantes


def probabilidade_resultado(vitorias_mandante, empates_mandante, derrotas_mandante,
                            vitorias_visitante, empates_visitante, derrotas_visitante):
    vetor_mandante = [3] * vitorias_mandante + [1] * empates_mandante + [0] * derrotas_mandante
    vetor_visitante = [0] * derrotas_visitante + [1] * empates_visitante + [3] * vitorias_visitante

    nr_comparacoes = min(len(vetor_mandante), len(vetor_visitante))
    if nr_comparacoes == 0:
        # sem histórico suficiente: retornar probabilidades uniformes
        return 0.33, 0.33, 0.34

    prob_mandante = prob_visitante = prob_empate = 0
    for jogo in range(nr_comparacoes):
        if vetor_mandante[jogo] > vetor_visitante[jogo]:
            prob_mandante += 1
        elif vetor_mandante[jogo] < vetor_visitante[jogo]:
            prob_visitante += 1
        else:
            prob_empate += 1

    return prob_mandante / nr_comparacoes, prob_visitante / nr_comparacoes, prob_empate / nr_comparacoes


# ---------- Função principal de simulação (adaptada) ----------

def executar_simulacao(ano, rodada_inicial=1, nr_simulacoes=10000, sleep_between_requests=0.25, st_progress_callback=None):
    # 1) pega times
    times = pega_times(ano, sleep_between_requests)

    # 2) preenche times e obtém jogos pendentes
    times, jogos_faltantes = preenche_times_e_jogos(times, ano, rodada_inicial, sleep_between_requests)

    # 3) calcula probabilidades para cada jogo pendente
    for i, jogo in enumerate(jogos_faltantes.jogos):
        mand, vis, _, _, _ = jogo
        prob_man, prob_vis, prob_emp = probabilidade_resultado(
            times[mand]['vitorias_mandante'], times[mand]['empates_mandante'], times[mand]['derrotas_mandante'],
            times[vis]['vitorias_visitante'], times[vis]['empates_visitante'], times[vis]['derrotas_visitante']
        )
        jogos_faltantes.jogos[i][2] = prob_man
        jogos_faltantes.jogos[i][3] = prob_man + prob_vis
        jogos_faltantes.jogos[i][4] = prob_man + prob_vis + prob_emp

    # 4) simulações Monte Carlo
    resultados = {um_time: [0] * 20 for um_time in times}

    for simulacao in range(nr_simulacoes):
        # barra de progresso opcional
        if st_progress_callback and simulacao % max(1, nr_simulacoes // 100) == 0:
            st_progress_callback(simulacao / nr_simulacoes)

        dic_pontuacao_simulada = {um_time: times[um_time]['pontos'] for um_time in times}

        for jogo in jogos_faltantes.jogos:
            mandante, visitante, prob_man, prob_vis, prob_emp = jogo
            sorteio = random()
            if sorteio < prob_man:
                dic_pontuacao_simulada[mandante] += 3.01
            elif sorteio < prob_vis:
                dic_pontuacao_simulada[visitante] += 3.01
            else:
                dic_pontuacao_simulada[mandante] += 1
                dic_pontuacao_simulada[visitante] += 1

        colocacao = sorted(dic_pontuacao_simulada.items(), key=lambda um_time: um_time[1], reverse=True)
        for lugar, um_time in enumerate(colocacao):
            resultados[um_time[0]][lugar] += 1

    # 5) retorna dataframe com probabilidades
    df = pd.DataFrame(resultados)
    df.index = df.index + 1
    df_prob = df / nr_simulacoes
    return df_prob


# ---------- Streamlit App ----------

def main():
    st.set_page_config(page_title="Simulador do Brasileirão", layout="wide")
    st.title("⚽ Simulador do Brasileirão (base: Gazeta Esportiva)")

    with st.sidebar:
        st.header("Configurações")
        ano = st.number_input("Ano", min_value=2010, max_value=2030, value=2025, step=1)
        rodada_inicial = st.number_input("Rodada inicial (para recalcular a partir de)", min_value=1, max_value=38, value=1, step=1)
        nr_simulacoes = st.number_input("Número de simulações", min_value=100, max_value=20000, value=10000, step=100)
        sleep_between_requests = st.number_input("Pausa entre requisições (s)", min_value=0.0, max_value=2.0, value=0.25, step=0.05)
        run = st.button("Executar simulação")

    placeholder_status = st.empty()
    progresso_bar = st.progress(0)

    if run:
        try:
            placeholder_status.info("Buscando e processando dados... (isso pode demorar alguns segundos)")

            def update_progress(p):
                progresso_bar.progress(min(1.0, max(0.0, p)))

            df_prob = executar_simulacao(ano, rodada_inicial, nr_simulacoes, sleep_between_requests,
                                         st_progress_callback=update_progress)

            placeholder_status.success("Simulação concluída com sucesso!")

            # Mostrar tabela resumida
            st.subheader("Probabilidades de posição (1 a 20)")
            st.dataframe(df_prob)

            # Mostrar gráficos - 20 gráficos, dois por linha
            st.subheader("Gráficos de distribuição por time")
            cols = st.columns(4)
            count = 0
            for time_name in df_prob.columns:
                fig, ax = plt.subplots(figsize=(4, 3))
                ax.plot(df_prob.index, df_prob[time_name], marker='o')
                ax.set_title(time_name)
                ax.set_xlabel('Posição')
                ax.set_ylabel('Probabilidade')
                ax.set_xticks(range(1, 21))
                ax.grid(True, linestyle='--', alpha=0.4)

                cols[count % 4].pyplot(fig)
                plt.close(fig)
                count += 1

            # Estatísticas rápidas
            st.subheader("Resumo: probabilidades-chave")
            resumo = pd.DataFrame(index=df_prob.columns)
            resumo['Campeonato (posição 1)'] = df_prob.loc[1]
            resumo['Top4 (soma posições 1-4)'] = df_prob.loc[1:4].sum()
            resumo['Z4 (soma posições 17-20)'] = df_prob.loc[17:20].sum()
            st.table(resumo.sort_values('Campeonato (posição 1)', ascending=False))

        except requests.HTTPError as e:
            placeholder_status.error(f"Erro nas requisições HTTP: {e}")
        except Exception as e:
            placeholder_status.error(f"Erro inesperado: {e}")


if __name__ == '__main__':
    main()
